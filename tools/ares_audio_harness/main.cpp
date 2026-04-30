#include <sfc/sfc.hpp>

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace fs = std::filesystem;

struct Sha1 {
  std::uint32_t h0 = 0x67452301;
  std::uint32_t h1 = 0xefcdab89;
  std::uint32_t h2 = 0x98badcfe;
  std::uint32_t h3 = 0x10325476;
  std::uint32_t h4 = 0xc3d2e1f0;
  std::uint64_t totalBytes = 0;
  std::array<std::uint8_t, 64> buffer{};
  std::size_t bufferSize = 0;

  static std::uint32_t rotl(std::uint32_t value, unsigned bits) {
    return (value << bits) | (value >> (32 - bits));
  }

  void processBlock(const std::uint8_t* block) {
    std::array<std::uint32_t, 80> w{};
    for (std::size_t i = 0; i < 16; ++i) {
      w[i] = (static_cast<std::uint32_t>(block[i * 4]) << 24) |
             (static_cast<std::uint32_t>(block[i * 4 + 1]) << 16) |
             (static_cast<std::uint32_t>(block[i * 4 + 2]) << 8) |
             static_cast<std::uint32_t>(block[i * 4 + 3]);
    }
    for (std::size_t i = 16; i < 80; ++i) {
      w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    }

    std::uint32_t a = h0;
    std::uint32_t b = h1;
    std::uint32_t c = h2;
    std::uint32_t d = h3;
    std::uint32_t e = h4;

    for (std::size_t i = 0; i < 80; ++i) {
      std::uint32_t f = 0;
      std::uint32_t k = 0;
      if (i < 20) {
        f = (b & c) | ((~b) & d);
        k = 0x5a827999;
      } else if (i < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (i < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      const std::uint32_t temp = rotl(a, 5) + f + e + k + w[i];
      e = d;
      d = c;
      c = rotl(b, 30);
      b = a;
      a = temp;
    }

    h0 += a;
    h1 += b;
    h2 += c;
    h3 += d;
    h4 += e;
  }

  void update(const std::uint8_t* data, std::size_t length) {
    totalBytes += length;
    while (length > 0) {
      const std::size_t copied = std::min<std::size_t>(length, 64 - bufferSize);
      std::copy(data, data + copied, buffer.begin() + static_cast<std::ptrdiff_t>(bufferSize));
      bufferSize += copied;
      data += copied;
      length -= copied;
      if (bufferSize == 64) {
        processBlock(buffer.data());
        bufferSize = 0;
      }
    }
  }

  std::string finalHex() {
    const std::uint64_t bitLength = totalBytes * 8;
    const std::uint8_t marker = 0x80;
    update(&marker, 1);
    const std::uint8_t zero = 0;
    while (bufferSize != 56) {
      update(&zero, 1);
    }
    std::array<std::uint8_t, 8> lengthBytes{};
    for (int i = 7; i >= 0; --i) {
      lengthBytes[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>(bitLength >> ((7 - i) * 8));
    }
    update(lengthBytes.data(), lengthBytes.size());

    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (auto word : {h0, h1, h2, h3, h4}) {
      out << std::setw(8) << word;
    }
    return out.str();
  }
};

struct Spc700IoWrite {
  std::uint16_t pc = 0;
  std::uint16_t address = 0;
  std::uint8_t data = 0;
  std::uint64_t instruction = 0;
  std::uint64_t shimTicks = 0;
  std::uint64_t sequence = 0;
};

struct Spc700IoEvent {
  std::string kind;
  Spc700IoWrite event;
};

struct Spc700SnapshotState {
  bool valid = false;
  std::array<std::uint8_t, 65536> ram{};
  std::array<std::uint8_t, 128> dspRegisters{};
  std::uint16_t pc = 0;
  std::uint16_t ya = 0;
  std::uint8_t x = 0;
  std::uint8_t s = 0;
  std::uint8_t p = 0;
  std::uint8_t keyOnData = 0;
  std::uint64_t keyOnEventIndex = 0;
  std::uint64_t instruction = 0;
  std::uint64_t shimTicks = 0;
};

enum class HostCommandMode {
  Disabled,
  Initial,
  AfterTimerEnable,
  OnFirstPort0Read,
};

std::string hostCommandModeName(HostCommandMode mode) {
  switch (mode) {
    case HostCommandMode::Disabled: return "disabled";
    case HostCommandMode::Initial: return "initial";
    case HostCommandMode::AfterTimerEnable: return "after_timer_enable";
    case HostCommandMode::OnFirstPort0Read: return "on_first_port0_read";
  }
  return "unknown";
}

struct Spc700EntryProbe : ares::SPC700 {
  std::array<std::uint8_t, 65536> ram{};
  std::array<std::uint8_t, 128> dspRegisters{};
  std::array<std::uint8_t, 4> cpuInputPorts{};
  std::array<std::uint8_t, 4> cpuOutputPorts{};
  std::vector<Spc700IoWrite> ioReads;
  std::vector<Spc700IoWrite> ioReadTail;
  std::vector<Spc700IoWrite> ioWrites;
  std::vector<Spc700IoWrite> ioWriteTail;
  std::vector<Spc700IoEvent> ioEventTail;
  std::vector<Spc700IoEvent> hostCommandIoWindow;
  std::vector<Spc700IoWrite> dspWrites;
  std::vector<Spc700IoWrite> dspWriteTail;
  std::array<std::uint64_t, 128> dspWriteRegisterCounts{};
  std::uint8_t dspAddress = 0;
  std::uint8_t timer0Target = 0;
  std::uint8_t timer0Counter = 0;
  std::uint32_t timer0Accumulator = 0;
  bool timer0Enable = false;
  std::uint8_t hostCommandPort0 = 0;
  HostCommandMode hostCommandMode = HostCommandMode::AfterTimerEnable;
  bool hostCommandInjected = false;
  std::uint64_t idleCycles = 0;
  std::uint64_t shimTicks = 0;
  std::uint64_t currentInstruction = 0;
  std::uint64_t ioEventSequence = 0;
  std::uint64_t ioReadCount = 0;
  std::uint64_t ioWriteCount = 0;
  std::uint64_t dspWriteCount = 0;
  std::uint64_t keyOnEventCount = 0;
  std::uint64_t keyOffEventCount = 0;
  std::uint64_t timer0OutputReadCount = 0;
  std::uint8_t lastKeyOnData = 0;
  std::uint8_t lastKeyOffData = 0;
  bool hostCommandInjectionRecorded = false;
  bool firstHostCommandReadRecorded = false;
  bool hostCommandIoWindowStarted = false;
  std::size_t hostCommandIoWindowRemaining = 0;
  Spc700IoWrite hostCommandInjection;
  Spc700IoWrite firstHostCommandRead;
  Spc700SnapshotState lastKeyOnSnapshot;

  Spc700IoWrite makeIoRecord(std::uint16_t address, std::uint8_t data) {
    return {
      static_cast<std::uint16_t>(r.pc.w),
      address,
      data,
      currentInstruction,
      shimTicks,
      ++ioEventSequence,
    };
  }

  void injectHostCommandPort0() {
    if (!hostCommandPort0 || hostCommandInjected) return;
    cpuInputPorts[0] = hostCommandPort0;
    hostCommandInjected = true;
    hostCommandInjection = makeIoRecord(0x00f4, hostCommandPort0);
    hostCommandInjectionRecorded = true;
  }

  void rememberIoEvent(std::string kind, const Spc700IoWrite& event) {
    Spc700IoEvent ioEvent{std::move(kind), event};
    ioEventTail.push_back(ioEvent);
    if (ioEventTail.size() > 64) ioEventTail.erase(ioEventTail.begin());
    if (hostCommandIoWindowStarted && hostCommandIoWindowRemaining > 0) {
      hostCommandIoWindow.push_back(ioEvent);
      --hostCommandIoWindowRemaining;
    }
  }

  void startHostCommandIoWindow() {
    if (hostCommandIoWindowStarted) return;
    hostCommandIoWindow = ioEventTail;
    hostCommandIoWindowStarted = true;
    hostCommandIoWindowRemaining = 64;
  }

  void captureLastKeyOnSnapshot(std::uint8_t rawData) {
    lastKeyOnSnapshot.valid = true;
    lastKeyOnSnapshot.ram = ram;
    lastKeyOnSnapshot.dspRegisters = dspRegisters;
    lastKeyOnSnapshot.pc = static_cast<std::uint16_t>(r.pc.w);
    lastKeyOnSnapshot.ya = static_cast<std::uint16_t>(r.ya.w);
    lastKeyOnSnapshot.x = static_cast<std::uint8_t>(r.x);
    lastKeyOnSnapshot.s = static_cast<std::uint8_t>(r.s);
    lastKeyOnSnapshot.p = static_cast<std::uint8_t>(static_cast<unsigned>(r.p));
    lastKeyOnSnapshot.keyOnData = rawData;
    lastKeyOnSnapshot.keyOnEventIndex = keyOnEventCount;
    lastKeyOnSnapshot.instruction = currentInstruction;
    lastKeyOnSnapshot.shimTicks = shimTicks;
  }

  void tickShim() {
    ++shimTicks;
    if (!timer0Enable) return;
    const std::uint32_t target = timer0Target ? timer0Target : 0x100;
    // This is a diagnostic progress shim, not a hardware clock model. It lets
    // the driver escape timer waits so we can locate the next semantic gate.
    if (++timer0Accumulator < target) return;
    timer0Accumulator = 0;
    timer0Counter = static_cast<std::uint8_t>((timer0Counter + 1) & 0x0f);
  }

  auto idle() -> void override {
    ++idleCycles;
    tickShim();
  }

  auto read(n16 address) -> n8 override {
    tickShim();
    const std::uint16_t rawAddress = static_cast<std::uint16_t>(address);
    std::uint8_t data = ram[rawAddress];
    if (rawAddress == 0x00f0 || rawAddress == 0x00f1) {
      data = 0;
    } else if (rawAddress == 0x00f2) {
      data = dspAddress;
    } else if (rawAddress == 0x00f3) {
      data = dspRegisters[dspAddress & 0x7f];
    } else if (rawAddress >= 0x00f4 && rawAddress <= 0x00f7) {
      if (rawAddress == 0x00f4 && hostCommandMode == HostCommandMode::OnFirstPort0Read) {
        injectHostCommandPort0();
      }
      data = cpuInputPorts[rawAddress - 0x00f4];
    } else if (rawAddress >= 0x00fa && rawAddress <= 0x00fc) {
      data = 0;
    } else if (rawAddress == 0x00fd) {
      data = timer0Counter;
      timer0Counter = 0;
      ++timer0OutputReadCount;
    } else if (rawAddress == 0x00fe || rawAddress == 0x00ff) {
      data = 0;
    }
    if (rawAddress >= 0x00f0 && rawAddress <= 0x00ff) {
      ++ioReadCount;
      const Spc700IoWrite record = makeIoRecord(rawAddress, data);
      if (ioReads.size() < 128) {
        ioReads.push_back(record);
      }
      ioReadTail.push_back(record);
      if (ioReadTail.size() > 128) ioReadTail.erase(ioReadTail.begin());
      rememberIoEvent("read", record);
      if (rawAddress == 0x00f4 && hostCommandPort0 && data == hostCommandPort0 && !firstHostCommandReadRecorded) {
        firstHostCommandRead = record;
        firstHostCommandReadRecorded = true;
        startHostCommandIoWindow();
      }
    }
    return data;
  }

  auto write(n16 address, n8 data) -> void override {
    tickShim();
    const std::uint16_t rawAddress = static_cast<std::uint16_t>(address);
    const std::uint8_t rawData = static_cast<std::uint8_t>(data);
    ram[rawAddress] = rawData;
    if (rawAddress >= 0x00f0 && rawAddress <= 0x00ff) {
      ++ioWriteCount;
      const Spc700IoWrite record = makeIoRecord(rawAddress, rawData);
      if (ioWrites.size() < 128) {
        ioWrites.push_back(record);
      }
      ioWriteTail.push_back(record);
      if (ioWriteTail.size() > 128) ioWriteTail.erase(ioWriteTail.begin());
      rememberIoEvent("write", record);
    }
    if (rawAddress == 0x00f2) {
      dspAddress = rawData & 0x7f;
    } else if (rawAddress == 0x00f3) {
      if (!(dspAddress & 0x80)) {
        dspRegisters[dspAddress & 0x7f] = rawData;
      }
      ++dspWriteCount;
      const std::uint8_t dspRegister = dspAddress & 0x7f;
      ++dspWriteRegisterCounts[dspRegister];
      if (dspRegister == 0x4c && rawData) {
        ++keyOnEventCount;
        lastKeyOnData = rawData;
        captureLastKeyOnSnapshot(rawData);
      }
      if (dspRegister == 0x5c && rawData) {
        ++keyOffEventCount;
        lastKeyOffData = rawData;
      }
      if (dspWrites.size() < 128) {
        dspWrites.push_back(makeIoRecord(dspAddress, rawData));
      }
      dspWriteTail.push_back(makeIoRecord(dspAddress, rawData));
      if (dspWriteTail.size() > 128) dspWriteTail.erase(dspWriteTail.begin());
    } else if (rawAddress == 0x00f1) {
      const bool nextTimer0Enable = (rawData & 0x01) != 0;
      if (!timer0Enable && nextTimer0Enable) {
        timer0Counter = 0;
        timer0Accumulator = 0;
      }
      timer0Enable = nextTimer0Enable;
      if (timer0Enable && hostCommandMode == HostCommandMode::AfterTimerEnable) {
        injectHostCommandPort0();
      }
      if (rawData & 0x10) {
        cpuInputPorts[0] = 0;
        cpuInputPorts[1] = 0;
      }
      if (rawData & 0x20) {
        cpuInputPorts[2] = 0;
        cpuInputPorts[3] = 0;
      }
    } else if (rawAddress >= 0x00f4 && rawAddress <= 0x00f7) {
      cpuOutputPorts[rawAddress - 0x00f4] = rawData;
    } else if (rawAddress == 0x00fa) {
      timer0Target = rawData;
    }
  }

  auto synchronizing() const -> bool override {
    return false;
  }

  auto readDisassembler(n16 address) -> n8 override {
    return ram[static_cast<std::uint16_t>(address)];
  }
};

std::vector<std::uint8_t> readBytes(const fs::path& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("could not open " + path.string());
  return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

std::string readText(const fs::path& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("could not open " + path.string());
  return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

void writeText(const fs::path& path, const std::string& text) {
  fs::create_directories(path.parent_path());
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("could not write " + path.string());
  out << text;
}

void writeBytes(const fs::path& path, const std::vector<std::uint8_t>& data) {
  fs::create_directories(path.parent_path());
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("could not write " + path.string());
  out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
}

std::string sha1Hex(const std::vector<std::uint8_t>& data) {
  Sha1 sha1;
  sha1.update(data.data(), data.size());
  return sha1.finalHex();
}

std::string sha1Hex(const std::uint8_t* data, std::size_t size) {
  Sha1 sha1;
  sha1.update(data, size);
  return sha1.finalHex();
}

std::string jsonEscape(std::string_view text) {
  std::ostringstream out;
  for (char ch : text) {
    switch (ch) {
      case '\\': out << "\\\\"; break;
      case '"': out << "\\\""; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default: out << ch; break;
    }
  }
  return out.str();
}

std::string unescapeJsonString(std::string_view text) {
  std::string out;
  out.reserve(text.size());
  for (std::size_t i = 0; i < text.size(); ++i) {
    if (text[i] != '\\' || i + 1 >= text.size()) {
      out.push_back(text[i]);
      continue;
    }
    const char next = text[++i];
    switch (next) {
      case '\\': out.push_back('\\'); break;
      case '"': out.push_back('"'); break;
      case 'n': out.push_back('\n'); break;
      case 'r': out.push_back('\r'); break;
      case 't': out.push_back('\t'); break;
      default: out.push_back(next); break;
    }
  }
  return out;
}

std::string extractStringField(const std::string& json, const std::string& field, std::size_t start = 0) {
  const std::string key = "\"" + field + "\"";
  const std::size_t keyPos = json.find(key, start);
  if (keyPos == std::string::npos) throw std::runtime_error("missing JSON field: " + field);
  const std::size_t colon = json.find(':', keyPos + key.size());
  const std::size_t quote = json.find('"', colon);
  if (colon == std::string::npos || quote == std::string::npos) {
    throw std::runtime_error("malformed JSON string field: " + field);
  }
  std::size_t end = quote + 1;
  bool escaped = false;
  for (; end < json.size(); ++end) {
    const char ch = json[end];
    if (escaped) {
      escaped = false;
    } else if (ch == '\\') {
      escaped = true;
    } else if (ch == '"') {
      return unescapeJsonString(std::string_view(json).substr(quote + 1, end - quote - 1));
    }
  }
  throw std::runtime_error("unterminated JSON string field: " + field);
}

int extractIntField(const std::string& json, const std::string& field, std::size_t start = 0) {
  const std::string key = "\"" + field + "\"";
  const std::size_t keyPos = json.find(key, start);
  if (keyPos == std::string::npos) throw std::runtime_error("missing JSON field: " + field);
  const std::size_t colon = json.find(':', keyPos + key.size());
  if (colon == std::string::npos) throw std::runtime_error("malformed JSON integer field: " + field);
  const std::size_t first = json.find_first_of("0123456789", colon + 1);
  const std::size_t last = json.find_first_not_of("0123456789", first);
  return std::stoi(json.substr(first, last - first));
}

fs::path argValue(int argc, char** argv, const std::string& name) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == name) return fs::path(argv[i + 1]);
  }
  return {};
}

bool hasFlag(int argc, char** argv, const std::string& name) {
  for (int i = 1; i < argc; ++i) {
    if (argv[i] == name) return true;
  }
  return false;
}

std::string hexByte(std::uint8_t value) {
  std::ostringstream out;
  out << "0x" << std::hex << std::uppercase << std::setw(2) << std::setfill('0') << static_cast<unsigned>(value);
  return out.str();
}

std::string hexWord(std::uint16_t value) {
  std::ostringstream out;
  out << "0x" << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << static_cast<unsigned>(value);
  return out.str();
}

HostCommandMode parseHostCommandMode(int argc, char** argv) {
  if (hasFlag(argc, argv, "--disable-diagnostic-command-preseed")) {
    return HostCommandMode::Disabled;
  }
  if (hasFlag(argc, argv, "--diagnostic-command-preseed-initial")) {
    return HostCommandMode::Initial;
  }
  if (hasFlag(argc, argv, "--diagnostic-command-preseed-on-first-read")) {
    return HostCommandMode::OnFirstPort0Read;
  }
  return HostCommandMode::AfterTimerEnable;
}

std::uint16_t spc700InstructionLength(std::uint8_t opcode) {
  switch (opcode) {
    case 0x3f:
    case 0x5f:
    case 0x78:
    case 0x8f:
    case 0xd5:
      return 3;
    case 0x2f:
    case 0x8d:
    case 0xab:
    case 0xad:
    case 0xc4:
    case 0xc8:
    case 0xcb:
    case 0xcd:
    case 0xd0:
    case 0xd7:
    case 0xd8:
    case 0xe8:
      return 2;
    default:
      return 1;
  }
}

constexpr std::size_t SPC700_PROBE_INSTRUCTION_LIMIT = 200000;

std::vector<std::uint8_t> buildDiagnosticSpcSnapshot(
  const std::vector<std::uint8_t>& apuRam,
  std::uint16_t pc,
  std::uint16_t ya,
  std::uint8_t x,
  std::uint8_t s,
  std::uint8_t p,
  const std::array<std::uint8_t, 128>& dspRegisters
) {
  std::vector<std::uint8_t> snapshot(0x10200, 0);
  const std::string signature = "SNES-SPC700 Sound File Data v0.30";
  std::copy(signature.begin(), signature.end(), snapshot.begin());
  snapshot[0x21] = 0x1a;
  snapshot[0x22] = 0x1a;
  snapshot[0x23] = 0x1a;
  snapshot[0x24] = 0x1a;
  snapshot[0x25] = static_cast<std::uint8_t>(pc & 0xff);
  snapshot[0x26] = static_cast<std::uint8_t>(pc >> 8);
  snapshot[0x27] = static_cast<std::uint8_t>(ya & 0xff);
  snapshot[0x28] = x;
  snapshot[0x29] = static_cast<std::uint8_t>(ya >> 8);
  snapshot[0x2a] = p;
  snapshot[0x2b] = s;
  std::copy(apuRam.begin(), apuRam.end(), snapshot.begin() + 0x100);
  std::copy(dspRegisters.begin(), dspRegisters.end(), snapshot.begin() + 0x10100);
  return snapshot;
}

std::vector<std::string> runSpc700EntryProbe(
  const std::vector<std::uint8_t>& apuRam,
  std::uint8_t hostCommandPort0,
  HostCommandMode hostCommandMode,
  std::vector<Spc700IoWrite>& ioReads,
  std::vector<Spc700IoWrite>& ioReadTail,
  std::vector<Spc700IoWrite>& ioWrites,
  std::vector<Spc700IoWrite>& ioWriteTail,
  std::vector<Spc700IoWrite>& dspWrites,
  std::vector<std::string>& tailTrace,
  std::size_t& executedInstructions,
  std::uint16_t& finalPc,
  std::uint16_t& finalYa,
  std::uint8_t& finalX,
  std::uint8_t& finalS,
  std::uint8_t& finalP,
  std::uint64_t& ioReadCount,
  std::uint64_t& ioWriteCount,
  std::uint64_t& dspWriteCount,
  std::uint64_t& keyOnEventCount,
  std::uint64_t& keyOffEventCount,
  std::uint8_t& lastKeyOnData,
  std::uint8_t& lastKeyOffData,
  std::uint64_t& shimTicks,
  std::uint64_t& timer0OutputReadCount,
  bool& hostCommandInjected,
  bool& hostCommandInjectionRecorded,
  bool& firstHostCommandReadRecorded,
  Spc700IoWrite& hostCommandInjection,
  Spc700IoWrite& firstHostCommandRead,
  std::array<std::uint8_t, 128>& finalDspRegisters,
  std::array<std::uint64_t, 128>& dspWriteRegisterCounts,
  std::vector<Spc700IoEvent>& hostCommandIoWindow,
  std::vector<Spc700IoWrite>& dspWriteTail,
  Spc700SnapshotState& lastKeyOnSnapshot
) {
  Spc700EntryProbe probe;
  probe.hostCommandPort0 = hostCommandPort0;
  probe.hostCommandMode = hostCommandMode;
  std::copy(apuRam.begin(), apuRam.end(), probe.ram.begin());
  probe.power();
  std::copy(apuRam.begin(), apuRam.end(), probe.ram.begin());
  probe.r.pc.w = 0x0500;
  if (probe.hostCommandMode == HostCommandMode::Initial) {
    probe.injectHostCommandPort0();
  }

  std::vector<std::string> trace;
  executedInstructions = 0;
  for (std::size_t step = 0; step < SPC700_PROBE_INSTRUCTION_LIMIT; ++step) {
    const std::uint16_t pc = static_cast<std::uint16_t>(probe.r.pc.w);
    const std::string line = hexWord(pc) + "  " + std::string(probe.disassembleInstruction(pc, probe.r.p.p));
    if (trace.size() < 32) {
      trace.push_back(line);
    }
    tailTrace.push_back(line);
    if (tailTrace.size() > 32) tailTrace.erase(tailTrace.begin());
    probe.currentInstruction = executedInstructions;
    probe.instruction();
    ++executedInstructions;
    if (probe.ioWrites.size() >= 4 && probe.r.pc.w == pc) break;
  }
  finalPc = static_cast<std::uint16_t>(probe.r.pc.w);
  finalYa = static_cast<std::uint16_t>(probe.r.ya.w);
  finalX = static_cast<std::uint8_t>(probe.r.x);
  finalS = static_cast<std::uint8_t>(probe.r.s);
  finalP = static_cast<std::uint8_t>(static_cast<unsigned>(probe.r.p));
  ioReadCount = probe.ioReadCount;
  ioWriteCount = probe.ioWriteCount;
  dspWriteCount = probe.dspWriteCount;
  keyOnEventCount = probe.keyOnEventCount;
  keyOffEventCount = probe.keyOffEventCount;
  lastKeyOnData = probe.lastKeyOnData;
  lastKeyOffData = probe.lastKeyOffData;
  shimTicks = probe.shimTicks;
  timer0OutputReadCount = probe.timer0OutputReadCount;
  hostCommandInjected = probe.hostCommandInjected;
  hostCommandInjectionRecorded = probe.hostCommandInjectionRecorded;
  firstHostCommandReadRecorded = probe.firstHostCommandReadRecorded;
  hostCommandInjection = probe.hostCommandInjection;
  firstHostCommandRead = probe.firstHostCommandRead;
  finalDspRegisters = probe.dspRegisters;
  dspWriteRegisterCounts = probe.dspWriteRegisterCounts;
  hostCommandIoWindow = probe.hostCommandIoWindow;
  ioReads = probe.ioReads;
  ioReadTail = probe.ioReadTail;
  ioWrites = probe.ioWrites;
  ioWriteTail = probe.ioWriteTail;
  dspWrites = probe.dspWrites;
  dspWriteTail = probe.dspWriteTail;
  lastKeyOnSnapshot = probe.lastKeyOnSnapshot;
  return trace;
}

int main(int argc, char** argv) {
  try {
    const fs::path jobPath = argValue(argc, argv, "--job");
    if (jobPath.empty()) {
      std::cerr << "usage: earthbound_ares_audio_harness --job <job.json> [--result <result.json>] [--disable-diagnostic-command-preseed|--diagnostic-command-preseed-initial|--diagnostic-command-preseed-on-first-read]\n";
      return 2;
    }
    const HostCommandMode hostCommandMode = parseHostCommandMode(argc, argv);
    const bool diagnosticCommandPreseedEnabled = hostCommandMode != HostCommandMode::Disabled;

    const std::string jobJson = readText(jobPath);
    const std::string fixturePathText = extractStringField(jobJson, "fixture_path");
    const std::string jobId = extractStringField(jobJson, "job_id");
    const std::string backendId = extractStringField(jobJson, "backend_id");
    const std::string inputSha1 = extractStringField(jobJson, "input_apu_ram_sha1");
    fs::path resultPath = argValue(argc, argv, "--result");
    if (resultPath.empty()) resultPath = fs::path(extractStringField(jobJson, "result_path"));
    resultPath = fs::absolute(resultPath);

    const fs::path fixturePath = fixturePathText;
    const std::string fixtureJson = readText(fixturePath);
    const std::size_t apuRamObject = fixtureJson.find("\"apu_ram\"");
    if (apuRamObject == std::string::npos) throw std::runtime_error("fixture is missing apu_ram object");
    const std::string apuRamPathText = extractStringField(fixtureJson, "path", apuRamObject);
    const std::string fixtureSha1 = extractStringField(fixtureJson, "sha1", apuRamObject);
    const int fixtureSize = extractIntField(fixtureJson, "size", apuRamObject);
    const int trackId = extractIntField(fixtureJson, "track_id");
    const std::string trackName = extractStringField(fixtureJson, "track_name");

    const std::vector<std::uint8_t> apuRam = readBytes(apuRamPathText);
    const std::string actualSha1 = sha1Hex(apuRam);
    if (apuRam.size() != 65536) throw std::runtime_error("APU RAM seed is not 65536 bytes");
    if (fixtureSize != 65536) throw std::runtime_error("fixture apu_ram size is not 65536");
    if (actualSha1 != fixtureSha1) throw std::runtime_error("APU RAM SHA-1 does not match fixture");
    if (actualSha1 != inputSha1) throw std::runtime_error("APU RAM SHA-1 does not match job");

    auto& dsp = ares::SuperFamicom::dsp;
    auto& smp = ares::SuperFamicom::smp;
    for (std::size_t i = 0; i < apuRam.size(); ++i) {
      dsp.apuram[i] = apuRam[i];
    }

    const std::uint16_t terminalEntry = 0x0500;
    std::vector<std::string> entryDisassembly;
    for (std::uint16_t pc = terminalEntry; pc < terminalEntry + 16;) {
      const std::uint8_t opcode = static_cast<std::uint8_t>(dsp.apuram[pc]);
      entryDisassembly.push_back(hexWord(pc) + "  " + std::string(smp.disassembleInstruction(pc, 0)));
      pc += spc700InstructionLength(opcode);
    }
    std::vector<std::string> helperDisassembly;
    for (std::uint16_t pc = 0x16a5; pc < 0x16c0;) {
      const std::uint8_t opcode = static_cast<std::uint8_t>(dsp.apuram[pc]);
      helperDisassembly.push_back(hexWord(pc) + "  " + std::string(smp.disassembleInstruction(pc, 0)));
      pc += spc700InstructionLength(opcode);
    }
    std::vector<Spc700IoWrite> probeIoReads;
    std::vector<Spc700IoWrite> probeIoReadTail;
    std::vector<Spc700IoWrite> probeIoWrites;
    std::vector<Spc700IoWrite> probeIoWriteTail;
    std::vector<Spc700IoWrite> probeDspWrites;
    std::vector<Spc700IoWrite> probeDspWriteTail;
    std::vector<std::string> entryExecutionTailTrace;
    std::size_t probeExecutedInstructions = 0;
    std::uint16_t probeFinalPc = 0;
    std::uint16_t probeFinalYa = 0;
    std::uint8_t probeFinalX = 0;
    std::uint8_t probeFinalS = 0;
    std::uint8_t probeFinalP = 0;
    std::uint64_t probeIoReadCount = 0;
    std::uint64_t probeIoWriteCount = 0;
    std::uint64_t probeDspWriteCount = 0;
    std::uint64_t probeKeyOnEventCount = 0;
    std::uint64_t probeKeyOffEventCount = 0;
    std::uint8_t probeLastKeyOnData = 0;
    std::uint8_t probeLastKeyOffData = 0;
    std::uint64_t probeShimTicks = 0;
    std::uint64_t probeTimer0OutputReadCount = 0;
    bool probeHostCommandInjected = false;
    bool probeHostCommandInjectionRecorded = false;
    bool probeFirstHostCommandReadRecorded = false;
    Spc700IoWrite probeHostCommandInjection;
    Spc700IoWrite probeFirstHostCommandRead;
    std::array<std::uint8_t, 128> probeFinalDspRegisters{};
    std::array<std::uint64_t, 128> probeDspWriteRegisterCounts{};
    std::vector<Spc700IoEvent> probeHostCommandIoWindow;
    Spc700SnapshotState probeLastKeyOnSnapshot;
    const std::uint8_t diagnosticHostCommand = static_cast<std::uint8_t>(trackId & 0xff);
    const std::vector<std::string> entryExecutionTrace = runSpc700EntryProbe(
      apuRam,
      diagnosticCommandPreseedEnabled ? diagnosticHostCommand : 0,
      hostCommandMode,
      probeIoReads,
      probeIoReadTail,
      probeIoWrites,
      probeIoWriteTail,
      probeDspWrites,
      entryExecutionTailTrace,
      probeExecutedInstructions,
      probeFinalPc,
      probeFinalYa,
      probeFinalX,
      probeFinalS,
      probeFinalP,
      probeIoReadCount,
      probeIoWriteCount,
      probeDspWriteCount,
      probeKeyOnEventCount,
      probeKeyOffEventCount,
      probeLastKeyOnData,
      probeLastKeyOffData,
      probeShimTicks,
      probeTimer0OutputReadCount,
      probeHostCommandInjected,
      probeHostCommandInjectionRecorded,
      probeFirstHostCommandReadRecorded,
      probeHostCommandInjection,
      probeFirstHostCommandRead,
      probeFinalDspRegisters,
      probeDspWriteRegisterCounts,
      probeHostCommandIoWindow,
      probeDspWriteTail,
      probeLastKeyOnSnapshot
    );

    fs::path lastKeyOnSpcPath = resultPath.parent_path() / "diagnostic-last-keyon-state.spc";
    std::vector<std::uint8_t> lastKeyOnSpc;
    std::string lastKeyOnSpcSha1;
    std::string lastKeyOnRamSha1;
    std::string lastKeyOnDspSha1;
    if (probeLastKeyOnSnapshot.valid) {
      const std::vector<std::uint8_t> lastKeyOnApuRam(
        probeLastKeyOnSnapshot.ram.begin(),
        probeLastKeyOnSnapshot.ram.end()
      );
      lastKeyOnSpc = buildDiagnosticSpcSnapshot(
        lastKeyOnApuRam,
        probeLastKeyOnSnapshot.pc,
        probeLastKeyOnSnapshot.ya,
        probeLastKeyOnSnapshot.x,
        probeLastKeyOnSnapshot.s,
        probeLastKeyOnSnapshot.p,
        probeLastKeyOnSnapshot.dspRegisters
      );
      writeBytes(lastKeyOnSpcPath, lastKeyOnSpc);
      lastKeyOnSpcSha1 = sha1Hex(lastKeyOnSpc);
      lastKeyOnRamSha1 = sha1Hex(probeLastKeyOnSnapshot.ram.data(), probeLastKeyOnSnapshot.ram.size());
      lastKeyOnDspSha1 = sha1Hex(
        probeLastKeyOnSnapshot.dspRegisters.data(),
        probeLastKeyOnSnapshot.dspRegisters.size()
      );
    }

    std::ostringstream capture;
    capture << "{\n";
    capture << "  \"schema\": \"earthbound-decomp.ares-state-capture.v1\",\n";
    capture << "  \"capture_kind\": \"apu_ram_seed_import\",\n";
    capture << "  \"backend_id\": \"ares\",\n";
    capture << "  \"job_id\": \"" << jsonEscape(jobId) << "\",\n";
    capture << "  \"track_id\": " << trackId << ",\n";
    capture << "  \"track_name\": \"" << jsonEscape(trackName) << "\",\n";
    capture << "  \"input_apu_ram_path\": \"" << jsonEscape(apuRamPathText) << "\",\n";
    capture << "  \"input_apu_ram_bytes\": " << apuRam.size() << ",\n";
    capture << "  \"input_apu_ram_sha1\": \"" << actualSha1 << "\",\n";
    capture << "  \"loaded_into_ares_sfc_dsp_apuram\": true,\n";
    capture << "  \"dsp_registers_public_snapshot\": {\n";
    capture << "    \"bytes\": 128,\n";
    capture << "    \"sha1\": \"" << sha1Hex(reinterpret_cast<const std::uint8_t*>(dsp.registers), 128) << "\",\n";
    capture << "    \"nonzero_count\": ";
    std::size_t nonzeroRegisters = 0;
    for (std::size_t i = 0; i < 128; ++i) {
      if (static_cast<std::uint8_t>(dsp.registers[i])) ++nonzeroRegisters;
    }
    capture << nonzeroRegisters << "\n";
    capture << "  },\n";
    capture << "  \"spc700_public_register_snapshot\": {\n";
    capture << "    \"pc\": \"" << hexWord(static_cast<std::uint16_t>(smp.r.pc.w)) << "\",\n";
    capture << "    \"ya\": \"" << hexWord(static_cast<std::uint16_t>(smp.r.ya.w)) << "\",\n";
    capture << "    \"x\": \"" << hexByte(static_cast<std::uint8_t>(smp.r.x)) << "\",\n";
    capture << "    \"s\": \"" << hexByte(static_cast<std::uint8_t>(smp.r.s)) << "\",\n";
    capture << "    \"p\": \"" << hexByte(static_cast<std::uint8_t>(static_cast<unsigned>(smp.r.p))) << "\",\n";
    capture << "    \"wait\": " << (smp.r.wait ? "true" : "false") << ",\n";
    capture << "    \"stop\": " << (smp.r.stop ? "true" : "false") << "\n";
    capture << "  },\n";
    capture << "  \"terminal_entry_probe\": {\n";
    capture << "    \"address\": \"" << hexWord(terminalEntry) << "\",\n";
    capture << "    \"source\": \"LOAD_SPC700_DATA terminal block destination\",\n";
    capture << "    \"first_16_bytes\": [";
    for (std::size_t i = 0; i < 16; ++i) {
      if (i) capture << ", ";
      capture << "\"" << hexByte(static_cast<std::uint8_t>(dsp.apuram[terminalEntry + i])) << "\"";
    }
    capture << "],\n";
    capture << "    \"ares_disassembly\": [\n";
    for (std::size_t i = 0; i < entryDisassembly.size(); ++i) {
      capture << "      \"" << jsonEscape(entryDisassembly[i]) << "\"";
      capture << (i + 1 == entryDisassembly.size() ? "\n" : ",\n");
    }
    capture << "    ]\n";
    capture << "  },\n";
    capture << "  \"driver_helper_16a5_probe\": {\n";
    capture << "    \"address\": \"0x16A5\",\n";
    capture << "    \"ares_disassembly\": [\n";
    for (std::size_t i = 0; i < helperDisassembly.size(); ++i) {
      capture << "      \"" << jsonEscape(helperDisassembly[i]) << "\"";
      capture << (i + 1 == helperDisassembly.size() ? "\n" : ",\n");
    }
    capture << "    ]\n";
    capture << "  },\n";
    capture << "  \"spc700_entry_execution_probe\": {\n";
    capture << "    \"engine\": \"ares::SPC700 with harness RAM/IO shim\",\n";
    capture << "    \"instruction_limit\": " << SPC700_PROBE_INSTRUCTION_LIMIT << ",\n";
    capture << "    \"executed_instructions\": " << probeExecutedInstructions << ",\n";
    capture << "    \"final_pc\": \"" << hexWord(probeFinalPc) << "\",\n";
    capture << "    \"final_registers\": {\"ya\": \"" << hexWord(probeFinalYa) << "\", \"x\": \"" << hexByte(probeFinalX) << "\", \"s\": \"" << hexByte(probeFinalS) << "\", \"p\": \"" << hexByte(probeFinalP) << "\"},\n";
    capture << "    \"apu_io_read_count\": " << probeIoReadCount << ",\n";
    capture << "    \"apu_io_write_count\": " << probeIoWriteCount << ",\n";
    capture << "    \"dsp_register_write_count\": " << probeDspWriteCount << ",\n";
    capture << "    \"dsp_key_on_event_count\": " << probeKeyOnEventCount << ",\n";
    capture << "    \"dsp_key_off_event_count\": " << probeKeyOffEventCount << ",\n";
    capture << "    \"dsp_last_key_on_data\": \"" << hexByte(probeLastKeyOnData) << "\",\n";
    capture << "    \"dsp_last_key_off_data\": \"" << hexByte(probeLastKeyOffData) << "\",\n";
    capture << "    \"diagnostic_shim_ticks\": " << probeShimTicks << ",\n";
    capture << "    \"timer0_output_read_count\": " << probeTimer0OutputReadCount << ",\n";
    capture << "    \"diagnostic_host_port0_preseed_enabled\": " << (diagnosticCommandPreseedEnabled ? "true" : "false") << ",\n";
    capture << "    \"diagnostic_host_port0_preseed_mode\": \"" << hostCommandModeName(hostCommandMode) << "\",\n";
    capture << "    \"diagnostic_host_port0_command\": \"" << hexByte(diagnosticHostCommand) << "\",\n";
    capture << "    \"diagnostic_host_port0_preseed_value\": \"" << hexByte(diagnosticCommandPreseedEnabled ? diagnosticHostCommand : 0) << "\",\n";
    capture << "    \"diagnostic_host_port0_injected_after_timer_enable\": " << (probeHostCommandInjected ? "true" : "false") << ",\n";
    capture << "    \"diagnostic_host_port0_injection\": ";
    if (probeHostCommandInjectionRecorded) {
      capture << "{\"pc\": \"" << hexWord(probeHostCommandInjection.pc) << "\", \"address\": \"" << hexWord(probeHostCommandInjection.address) << "\", \"data\": \"" << hexByte(probeHostCommandInjection.data) << "\", \"instruction\": " << probeHostCommandInjection.instruction << ", \"shim_ticks\": " << probeHostCommandInjection.shimTicks << ", \"sequence\": " << probeHostCommandInjection.sequence << "},\n";
    } else {
      capture << "null,\n";
    }
    capture << "    \"diagnostic_host_port0_first_read\": ";
    if (probeFirstHostCommandReadRecorded) {
      capture << "{\"pc\": \"" << hexWord(probeFirstHostCommandRead.pc) << "\", \"address\": \"" << hexWord(probeFirstHostCommandRead.address) << "\", \"data\": \"" << hexByte(probeFirstHostCommandRead.data) << "\", \"instruction\": " << probeFirstHostCommandRead.instruction << ", \"shim_ticks\": " << probeFirstHostCommandRead.shimTicks << ", \"sequence\": " << probeFirstHostCommandRead.sequence << "},\n";
    } else {
      capture << "null,\n";
    }
    capture << "    \"diagnostic_host_port0_io_window\": [\n";
    for (std::size_t i = 0; i < probeHostCommandIoWindow.size(); ++i) {
      const auto& ioEvent = probeHostCommandIoWindow[i];
      const auto& event = ioEvent.event;
      capture << "      {\"kind\": \"" << jsonEscape(ioEvent.kind) << "\", \"pc\": \"" << hexWord(event.pc) << "\", \"address\": \"" << hexWord(event.address) << "\", \"data\": \"" << hexByte(event.data) << "\", \"instruction\": " << event.instruction << ", \"shim_ticks\": " << event.shimTicks << ", \"sequence\": " << event.sequence << "}";
      capture << (i + 1 == probeHostCommandIoWindow.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"diagnostic_final_dsp_registers_sha1\": \"" << sha1Hex(probeFinalDspRegisters.data(), probeFinalDspRegisters.size()) << "\",\n";
    capture << "    \"last_key_on_snapshot\": {\n";
    capture << "      \"available\": " << (probeLastKeyOnSnapshot.valid ? "true" : "false");
    if (probeLastKeyOnSnapshot.valid) {
      capture << ",\n";
      capture << "      \"kind\": \"diagnostic_last_keyon_spc_snapshot\",\n";
      capture << "      \"path\": \"" << jsonEscape(lastKeyOnSpcPath.string()) << "\",\n";
      capture << "      \"bytes\": " << lastKeyOnSpc.size() << ",\n";
      capture << "      \"sha1\": \"" << lastKeyOnSpcSha1 << "\",\n";
      capture << "      \"ram_sha1\": \"" << lastKeyOnRamSha1 << "\",\n";
      capture << "      \"dsp_register_sha1\": \"" << lastKeyOnDspSha1 << "\",\n";
      capture << "      \"pc\": \"" << hexWord(probeLastKeyOnSnapshot.pc) << "\",\n";
      capture << "      \"registers\": {\"ya\": \"" << hexWord(probeLastKeyOnSnapshot.ya) << "\", \"x\": \"" << hexByte(probeLastKeyOnSnapshot.x) << "\", \"s\": \"" << hexByte(probeLastKeyOnSnapshot.s) << "\", \"p\": \"" << hexByte(probeLastKeyOnSnapshot.p) << "\"},\n";
      capture << "      \"key_on_event_index\": " << probeLastKeyOnSnapshot.keyOnEventIndex << ",\n";
      capture << "      \"instruction\": " << probeLastKeyOnSnapshot.instruction << ",\n";
      capture << "      \"shim_ticks\": " << probeLastKeyOnSnapshot.shimTicks << ",\n";
      capture << "      \"key_on_data\": \"" << hexByte(probeLastKeyOnSnapshot.keyOnData) << "\",\n";
      capture << "      \"dsp_kon_register\": \"" << hexByte(probeLastKeyOnSnapshot.dspRegisters[0x4c]) << "\",\n";
      capture << "      \"dsp_kof_register\": \"" << hexByte(probeLastKeyOnSnapshot.dspRegisters[0x5c]) << "\"\n";
    } else {
      capture << "\n";
    }
    capture << "    },\n";
    capture << "    \"access_log_limit_per_kind\": 128,\n";
    capture << "    \"timing_model\": \"instruction semantics plus rough timer0 progress shim and diagnostic APUIO0 track-command preseed; no SFC scheduler, DSP audio timing, or true CPU/APU synchronization\",\n";
    capture << "    \"first_trace\": [\n";
    for (std::size_t i = 0; i < entryExecutionTrace.size(); ++i) {
      capture << "      \"" << jsonEscape(entryExecutionTrace[i]) << "\"";
      capture << (i + 1 == entryExecutionTrace.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"tail_trace\": [\n";
    for (std::size_t i = 0; i < entryExecutionTailTrace.size(); ++i) {
      capture << "      \"" << jsonEscape(entryExecutionTailTrace[i]) << "\"";
      capture << (i + 1 == entryExecutionTailTrace.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"apu_io_reads\": [\n";
    for (std::size_t i = 0; i < probeIoReads.size(); ++i) {
      const auto& read = probeIoReads[i];
      capture << "      {\"pc\": \"" << hexWord(read.pc) << "\", \"address\": \"" << hexWord(read.address) << "\", \"data\": \"" << hexByte(read.data) << "\", \"instruction\": " << read.instruction << ", \"shim_ticks\": " << read.shimTicks << ", \"sequence\": " << read.sequence << "}";
      capture << (i + 1 == probeIoReads.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"apu_io_read_tail\": [\n";
    for (std::size_t i = 0; i < probeIoReadTail.size(); ++i) {
      const auto& read = probeIoReadTail[i];
      capture << "      {\"pc\": \"" << hexWord(read.pc) << "\", \"address\": \"" << hexWord(read.address) << "\", \"data\": \"" << hexByte(read.data) << "\", \"instruction\": " << read.instruction << ", \"shim_ticks\": " << read.shimTicks << ", \"sequence\": " << read.sequence << "}";
      capture << (i + 1 == probeIoReadTail.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"apu_io_writes\": [\n";
    for (std::size_t i = 0; i < probeIoWrites.size(); ++i) {
      const auto& write = probeIoWrites[i];
      capture << "      {\"pc\": \"" << hexWord(write.pc) << "\", \"address\": \"" << hexWord(write.address) << "\", \"data\": \"" << hexByte(write.data) << "\", \"instruction\": " << write.instruction << ", \"shim_ticks\": " << write.shimTicks << ", \"sequence\": " << write.sequence << "}";
      capture << (i + 1 == probeIoWrites.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"apu_io_write_tail\": [\n";
    for (std::size_t i = 0; i < probeIoWriteTail.size(); ++i) {
      const auto& write = probeIoWriteTail[i];
      capture << "      {\"pc\": \"" << hexWord(write.pc) << "\", \"address\": \"" << hexWord(write.address) << "\", \"data\": \"" << hexByte(write.data) << "\", \"instruction\": " << write.instruction << ", \"shim_ticks\": " << write.shimTicks << ", \"sequence\": " << write.sequence << "}";
      capture << (i + 1 == probeIoWriteTail.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"dsp_register_writes\": [\n";
    for (std::size_t i = 0; i < probeDspWrites.size(); ++i) {
      const auto& write = probeDspWrites[i];
      capture << "      {\"pc\": \"" << hexWord(write.pc) << "\", \"register\": \"" << hexByte(write.address & 0x7f) << "\", \"data\": \"" << hexByte(write.data) << "\", \"instruction\": " << write.instruction << ", \"shim_ticks\": " << write.shimTicks << ", \"sequence\": " << write.sequence << "}";
      capture << (i + 1 == probeDspWrites.size() ? "\n" : ",\n");
    }
    capture << "    ],\n";
    capture << "    \"dsp_register_write_counts\": {\n";
    bool wroteRegisterCount = false;
    for (std::size_t i = 0; i < probeDspWriteRegisterCounts.size(); ++i) {
      if (!probeDspWriteRegisterCounts[i]) continue;
      if (wroteRegisterCount) capture << ",\n";
      capture << "      \"" << hexByte(static_cast<std::uint8_t>(i)) << "\": " << probeDspWriteRegisterCounts[i];
      wroteRegisterCount = true;
    }
    if (wroteRegisterCount) capture << "\n";
    capture << "    },\n";
    capture << "    \"dsp_register_write_tail\": [\n";
    for (std::size_t i = 0; i < probeDspWriteTail.size(); ++i) {
      const auto& write = probeDspWriteTail[i];
      capture << "      {\"pc\": \"" << hexWord(write.pc) << "\", \"register\": \"" << hexByte(write.address & 0x7f) << "\", \"data\": \"" << hexByte(write.data) << "\", \"instruction\": " << write.instruction << ", \"shim_ticks\": " << write.shimTicks << ", \"sequence\": " << write.sequence << "}";
      capture << (i + 1 == probeDspWriteTail.size() ? "\n" : ",\n");
    }
    capture << "    ]\n";
    capture << "  },\n";
    capture << "  \"first_16_bytes\": [";
    for (std::size_t i = 0; i < 16; ++i) {
      if (i) capture << ", ";
      capture << "\"" << hexByte(static_cast<std::uint8_t>(dsp.apuram[i])) << "\"";
    }
    capture << "],\n";
    capture << "  \"renderer_boundary\": \"diagnostic only: no SMP boot, command handshake, DSP register finalization, or PCM render yet\"\n";
    capture << "}\n";

    const fs::path capturePath = resultPath.parent_path() / "ares-state-capture.json";
    writeText(capturePath, capture.str());
    const std::vector<std::uint8_t> captureBytes = readBytes(capturePath);
    const std::string captureSha1 = sha1Hex(captureBytes);
    const std::vector<std::uint8_t> diagnosticSpc = buildDiagnosticSpcSnapshot(
      apuRam,
      probeFinalPc,
      probeFinalYa,
      probeFinalX,
      probeFinalS,
      probeFinalP,
      probeFinalDspRegisters
    );
    const fs::path spcPath = resultPath.parent_path() / "diagnostic-driver-state.spc";
    writeBytes(spcPath, diagnosticSpc);
    const std::string spcSha1 = sha1Hex(diagnosticSpc);

    std::ostringstream result;
    result << "{\n";
    result << "  \"schema\": \"earthbound-decomp.audio-backend-result.v1\",\n";
    result << "  \"job_id\": \"" << jsonEscape(jobId) << "\",\n";
    result << "  \"backend_id\": \"" << jsonEscape(backendId) << "\",\n";
    result << "  \"backend_version\": \"ares-harness-diagnostic-spc-snapshot-0.9\",\n";
    result << "  \"status\": \"unsupported\",\n";
    result << "  \"input_fixture_path\": \"" << jsonEscape(fixturePathText) << "\",\n";
    result << "  \"input_apu_ram_sha1\": \"" << actualSha1 << "\",\n";
    result << "  \"outputs\": [\n";
    result << "    {\n";
    result << "      \"kind\": \"state_capture_json\",\n";
    result << "      \"path\": \"" << jsonEscape(capturePath.string()) << "\",\n";
    result << "      \"bytes\": " << captureBytes.size() << ",\n";
    result << "      \"sha1\": \"" << captureSha1 << "\"\n";
    result << "    },\n";
    result << "    {\n";
    result << "      \"kind\": \"complete_spc_snapshot\",\n";
    result << "      \"path\": \"" << jsonEscape(spcPath.string()) << "\",\n";
    result << "      \"bytes\": " << diagnosticSpc.size() << ",\n";
    result << "      \"sha1\": \"" << spcSha1 << "\"\n";
    result << "    }\n";
    result << "  ],\n";
    result << "  \"diagnostics\": {\n";
    result << "    \"execution_mode\": \"native_ares_linked_harness\",\n";
    result << "    \"handshake_policy\": \"diagnostic_apuio0_track_command_preseed\",\n";
    result << "    \"timing_basis\": \"diagnostic_timer0_shim\",\n";
    result << "    \"message\": \"Loaded the diagnostic APU RAM seed into ares::SuperFamicom::dsp.apuram and ran the SPC700 terminal entry with a rough timer0 progress shim plus a diagnostic APUIO0 track-command preseed. The capture JSON includes a real last-key-on SPC snapshot when the probe reaches a nonzero DSP KON write and now records instruction/sequence evidence around host-command injection, host-command reads, and IO/DSP events. PCM/WAV export still requires full boot/handshake/timing work.\"\n";
    result << "  }\n";
    result << "}\n";
    writeText(resultPath, result.str());

    std::cout << "Wrote ares diagnostic backend result -> " << resultPath.string() << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "ares audio harness failed: " << error.what() << "\n";
    return 1;
  }
}
