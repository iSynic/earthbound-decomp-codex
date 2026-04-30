#include <sfc/sfc.hpp>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;

std::vector<std::uint8_t> readBytes(const fs::path& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("could not open " + path.string());
  return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

void writeBytes(const fs::path& path, const std::vector<std::uint8_t>& data) {
  fs::create_directories(path.parent_path());
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("could not write " + path.string());
  out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
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

std::string jsonEscape(const std::string& text) {
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

fs::path argPath(int argc, char** argv, const std::string& name) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == name) return fs::path(argv[i + 1]);
  }
  return {};
}

int argInt(int argc, char** argv, const std::string& name, int fallback) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == name) return std::stoi(argv[i + 1], nullptr, 0);
  }
  return fallback;
}

bool hasFlag(int argc, char** argv, const std::string& name) {
  for (int i = 1; i < argc; ++i) {
    if (argv[i] == name) return true;
  }
  return false;
}

struct CpuInstructionApuWriteProbe : ares::WDC65816 {
  std::uint8_t command = 0;
  std::vector<std::uint8_t> programBytes;
  std::vector<std::uint8_t> callerBytes;
  std::vector<std::uint8_t> changeMusicTailBytes;
  std::vector<std::uint8_t> changeMusicBytes;
  std::vector<std::uint8_t> changeMusicHelperBytes;
  std::vector<std::uint8_t> musicDatasetBytes;
  std::vector<std::uint8_t> musicPackPointerBytes;
  std::vector<std::uint8_t> romBytes;
  std::unordered_map<std::uint32_t, std::uint8_t> memoryWrites;
  bool applyLoadSpc700DataStreams = false;
  int writesTo2140 = 0;
  int loadSpc700DataStubCalls = 0;
  int loadSpc700DataAppliedStreams = 0;
  int loadSpc700DataAppliedBlocks = 0;
  int loadSpc700DataAppliedBytes = 0;
  int loadSpc700DataApplyErrors = 0;
  std::uint16_t lastLoadSpc700DataA = 0;
  std::uint16_t lastLoadSpc700DataX = 0;
  std::vector<std::pair<std::uint16_t, std::uint16_t>> loadSpc700DataStubArgs;
  int instructionCount = 0;
  std::uint8_t lastWriteData = 0;
  std::uint32_t lastWriteAddress = 0;
  std::uint32_t finalPc = 0;
  std::string routine = "sep_20_sta_002140_prefix_of_C0ABBD";
  std::vector<std::string> trace;
  bool callThroughJsl = false;
  bool callThroughChangeMusicTail = false;
  bool callThroughFullChangeMusic = false;
  bool preSatisfyChangeMusicPacks = true;
  static constexpr std::uint32_t callerBase = 0x008000;
  static constexpr std::uint32_t routineBase = 0xC0ABBD;
  static constexpr std::uint32_t stopMusicBase = 0xC0ABC6;
  static constexpr std::uint32_t playSoundUnknownBase = 0xC0AC01;
  static constexpr std::uint32_t stopMusicTransitionBase = 0xC0AC0C;
  static constexpr std::uint32_t loadSpc700DataBase = 0xC0AB06;
  static constexpr std::uint32_t changeMusicTailBase = 0xC4FD0E;
  static constexpr std::uint32_t changeMusicHelperBase = 0xC4FB42;
  static constexpr std::uint32_t changeMusicBase = 0xC4FBBD;
  static constexpr std::uint32_t musicDatasetTableBase = 0xC4F70A;
  static constexpr std::uint32_t musicPackPointerTableBase = 0xC4F947;

  static auto read16(const std::vector<std::uint8_t>& bytes, std::size_t offset) -> std::uint16_t {
    return static_cast<std::uint16_t>(bytes[offset] | (bytes[offset + 1] << 8));
  }

  static auto hiromOffset(std::uint8_t bank, std::uint16_t address) -> std::size_t {
    if (bank < 0xC0) throw std::runtime_error("LOAD_SPC700_DATA pointer bank is not canonical HiROM");
    return static_cast<std::size_t>(bank - 0xC0) * 0x10000u + address;
  }

  auto applyLoadSpc700DataStream(std::uint16_t address, std::uint16_t bankWord) -> void {
    try {
      const std::uint8_t bank = static_cast<std::uint8_t>(bankWord & 0xff);
      std::size_t cursor = hiromOffset(bank, address);
      if (cursor >= romBytes.size()) throw std::runtime_error("LOAD_SPC700_DATA pointer outside ROM");
      ++loadSpc700DataAppliedStreams;
      while (cursor + 2 <= romBytes.size()) {
        const std::uint16_t count = read16(romBytes, cursor);
        cursor += 2;
        if (count == 0) return;
        if (cursor + 2 > romBytes.size()) throw std::runtime_error("truncated LOAD_SPC700_DATA destination");
        const std::uint16_t destination = read16(romBytes, cursor);
        cursor += 2;
        if (cursor + count > romBytes.size()) throw std::runtime_error("truncated LOAD_SPC700_DATA payload");
        if (static_cast<std::uint32_t>(destination) + count > 0x10000) throw std::runtime_error("LOAD_SPC700_DATA payload writes past APU RAM");
        std::copy(romBytes.begin() + cursor, romBytes.begin() + cursor + count, ares::SuperFamicom::dsp.apuram + destination);
        cursor += count;
        ++loadSpc700DataAppliedBlocks;
        loadSpc700DataAppliedBytes += count;
      }
      throw std::runtime_error("LOAD_SPC700_DATA stream missing terminal block");
    } catch (const std::exception&) {
      ++loadSpc700DataApplyErrors;
    }
  }

  auto idle() -> void override {}
  auto lastCycle() -> void override {}
  auto interruptPending() const -> bool override { return false; }
  auto synchronizing() const -> bool override { return false; }

  auto read(n24 address) -> n8 override {
    const std::uint32_t rawAddress = static_cast<std::uint32_t>(address);
    if (auto found = memoryWrites.find(rawAddress); found != memoryWrites.end()) {
      return found->second;
    }
    if (callThroughFullChangeMusic) {
      if (rawAddress >= changeMusicBase && rawAddress < changeMusicBase + changeMusicBytes.size()) {
        return changeMusicBytes[rawAddress - changeMusicBase];
      }
      if (rawAddress >= changeMusicHelperBase && rawAddress < changeMusicHelperBase + changeMusicHelperBytes.size()) {
        return changeMusicHelperBytes[rawAddress - changeMusicHelperBase];
      }
      if (rawAddress >= routineBase && rawAddress < routineBase + programBytes.size()) {
        return programBytes[rawAddress - routineBase];
      }
      if (rawAddress == loadSpc700DataBase) {
        ++loadSpc700DataStubCalls;
        lastLoadSpc700DataA = static_cast<std::uint16_t>(r.a.w);
        lastLoadSpc700DataX = static_cast<std::uint16_t>(r.x.w);
        loadSpc700DataStubArgs.push_back({lastLoadSpc700DataA, lastLoadSpc700DataX});
        if (applyLoadSpc700DataStreams) {
          applyLoadSpc700DataStream(lastLoadSpc700DataA, lastLoadSpc700DataX);
        }
        return 0x6b; // RTL stub for the stream transfer; call arguments are recorded.
      }
      if (rawAddress == playSoundUnknownBase || rawAddress == stopMusicTransitionBase || rawAddress == stopMusicBase) {
        return 0x6b; // RTL stub for helpers whose effects are pre-satisfied by the fixture state.
      }
      if (rawAddress == 0x00b4b6 || rawAddress == 0x00b4b7) return 0x01; // CreditsPlaybackActive: skip PLAY_SOUND_UNKNOWN0.
      if (rawAddress == 0x00b53b) return 0x00; // CurrentMusicTrack low: force change path.
      if (rawAddress == 0x00b53c) return 0x00;
      const int trackIndex = static_cast<int>(command) - 1;
      const int rowOffset = trackIndex * 3;
      if (rawAddress >= musicDatasetTableBase && rawAddress < musicDatasetTableBase + musicDatasetBytes.size()) {
        return musicDatasetBytes[rawAddress - musicDatasetTableBase];
      }
      if (rawAddress >= musicPackPointerTableBase && rawAddress < musicPackPointerTableBase + musicPackPointerBytes.size()) {
        return musicPackPointerBytes[rawAddress - musicPackPointerTableBase];
      }
      if (preSatisfyChangeMusicPacks && rowOffset >= 0 && rowOffset + 2 < static_cast<int>(musicDatasetBytes.size())) {
        if (rawAddress == 0x00b53d) return musicDatasetBytes[rowOffset + 0]; // CurrentPrimarySamplePack low.
        if (rawAddress == 0x00b53e) return 0x00;
        if (rawAddress == 0x00b53f) return musicDatasetBytes[rowOffset + 1]; // CurrentSecondarySamplePack low.
        if (rawAddress == 0x00b540) return 0x00;
        if (rawAddress == 0x00b541) return musicDatasetBytes[rowOffset + 2]; // CurrentSequencePack low.
        if (rawAddress == 0x00b542) return 0x00;
      }
      if (!preSatisfyChangeMusicPacks) {
        if (rawAddress >= 0x00b53d && rawAddress <= 0x00b548) return 0xff;
      }
      if (rawAddress == 0x0001fb) return 0x03; // final RTL target low byte ($008003 + 1)
      if (rawAddress == 0x0001fc) return 0x80; // final RTL target high byte
      if (rawAddress == 0x0001fd) return 0x00; // final RTL target bank
    } else if (callThroughChangeMusicTail) {
      if (rawAddress >= changeMusicTailBase && rawAddress < changeMusicTailBase + changeMusicTailBytes.size()) {
        return changeMusicTailBytes[rawAddress - changeMusicTailBase];
      }
      if (rawAddress >= routineBase && rawAddress < routineBase + programBytes.size()) {
        return programBytes[rawAddress - routineBase];
      }
      if (rawAddress == 0x000010) return static_cast<std::uint8_t>((command - 1) & 0xff);
      if (rawAddress == 0x000011) return 0x00;
      if (rawAddress == 0x0001f9) return 0x00; // PLD low byte
      if (rawAddress == 0x0001fa) return 0x00; // PLD high byte
      if (rawAddress == 0x0001fb) return 0x03; // final RTL target low byte ($008003 + 1)
      if (rawAddress == 0x0001fc) return 0x80; // final RTL target high byte
      if (rawAddress == 0x0001fd) return 0x00; // final RTL target bank
    } else if (callThroughJsl) {
      if (rawAddress >= callerBase && rawAddress < callerBase + callerBytes.size()) {
        return callerBytes[rawAddress - callerBase];
      }
      if (rawAddress >= routineBase && rawAddress < routineBase + programBytes.size()) {
        return programBytes[rawAddress - routineBase];
      }
    } else if (rawAddress >= callerBase && rawAddress < callerBase + programBytes.size()) {
      return programBytes[rawAddress - callerBase];
    }
    if (rawAddress == 0x0001fb) return 0x00;
    if (rawAddress == 0x0001fc) return 0xc0;
    if (rawAddress == 0x0001fd) return 0x00;
    return 0xea;  // nop if the probe accidentally reads beyond the modeled prefix
  }

  auto write(n24 address, n8 data) -> void override {
    const std::uint32_t rawAddress = static_cast<std::uint32_t>(address);
    lastWriteAddress = rawAddress;
    lastWriteData = static_cast<std::uint8_t>(data);
    if (rawAddress == 0x002140) {
      ++writesTo2140;
      ares::SuperFamicom::cpu.writeAPU(0x2140, data);
    } else {
      memoryWrites[rawAddress] = static_cast<std::uint8_t>(data);
    }
  }

  auto run(std::uint8_t commandByte, bool fullRoutine, bool useJslCaller, bool useChangeMusicTail, bool useFullChangeMusic, bool usePresatisfiedPacks, bool useLoadStreamApply, std::vector<std::uint8_t> program, std::vector<std::uint8_t> tailProgram, std::vector<std::uint8_t> changeMusicProgram, std::vector<std::uint8_t> changeMusicHelperProgram, std::vector<std::uint8_t> musicDatasetProgram, std::vector<std::uint8_t> musicPackPointerProgram, std::vector<std::uint8_t> romProgram, const std::string& routineName) -> bool {
    command = commandByte;
    programBytes = std::move(program);
    changeMusicTailBytes = std::move(tailProgram);
    changeMusicBytes = std::move(changeMusicProgram);
    changeMusicHelperBytes = std::move(changeMusicHelperProgram);
    musicDatasetBytes = std::move(musicDatasetProgram);
    musicPackPointerBytes = std::move(musicPackPointerProgram);
    romBytes = std::move(romProgram);
    routine = routineName;
    callThroughJsl = useJslCaller;
    callThroughChangeMusicTail = useChangeMusicTail;
    callThroughFullChangeMusic = useFullChangeMusic;
    preSatisfyChangeMusicPacks = usePresatisfiedPacks;
    applyLoadSpc700DataStreams = useLoadStreamApply;
    callerBytes = {
      0x22, 0xbd, 0xab, 0xc0, // jsl $C0ABBD
      0xea                    // nop landing byte after rtl
    };
    memoryWrites.clear();
    loadSpc700DataStubCalls = 0;
    loadSpc700DataAppliedStreams = 0;
    loadSpc700DataAppliedBlocks = 0;
    loadSpc700DataAppliedBytes = 0;
    loadSpc700DataApplyErrors = 0;
    lastLoadSpc700DataA = 0;
    lastLoadSpc700DataX = 0;
    loadSpc700DataStubArgs.clear();
    power();
    r.pc.d = callThroughFullChangeMusic ? changeMusicBase : (callThroughChangeMusicTail ? changeMusicTailBase : callerBase);
    r.a.w = commandByte;
    r.x.w = 0;
    r.y.w = 0;
    r.s.w = callThroughFullChangeMusic ? 0x01fa : (callThroughChangeMusicTail ? 0x01f8 : 0x01fa);
    r.d.w = 0;
    r.b = 0;
    r.e = 0;
    r.p = 0x00;
    const int maxInstructions = callThroughFullChangeMusic ? 240 : (callThroughChangeMusicTail ? 10 : (callThroughJsl ? 5 : (fullRoutine ? 4 : 2)));
    instructionCount = 0;
    for (int index = 0; index < maxInstructions; ++index) {
      instruction();
      ++instructionCount;
      if (callThroughFullChangeMusic && writesTo2140 && static_cast<std::uint32_t>(r.pc.d) == 0x008004) break;
      if (!fullRoutine && !callThroughChangeMusicTail && !callThroughFullChangeMusic && writesTo2140) break;
    }
    finalPc = static_cast<std::uint32_t>(r.pc.d);
    const bool writeOk = writesTo2140 == 1 && lastWriteAddress == 0x002140 && lastWriteData == command;
    if (callThroughFullChangeMusic) return writeOk && finalPc == 0x008004;
    if (callThroughChangeMusicTail) return writeOk && finalPc == 0x008004;
    if (callThroughJsl) return writeOk && finalPc == 0x008004;
    return fullRoutine ? writeOk && finalPc == 0x00c001 : writeOk;
  }
};

std::vector<std::uint8_t> c0abbdPrefixProgram() {
  return {
    0xe2, 0x20,             // sep #$20
    0x8f, 0x40, 0x21, 0x00  // sta.l $002140
  };
}

std::vector<std::uint8_t> c0abbdFullProgram() {
  return {
    0xe2, 0x20,             // sep #$20
    0x8f, 0x40, 0x21, 0x00, // sta.l $002140
    0xc2, 0x30,             // rep #$30
    0x6b                    // rtl
  };
}

std::string runCpuInstructionApuWrite(
  std::uint8_t command,
  bool fullRoutine,
  bool useJslCaller,
  bool useChangeMusicTail,
  bool useFullChangeMusic,
  bool preSatisfyChangeMusicPacks,
  const std::vector<std::uint8_t>& routineBytes = {},
  const std::vector<std::uint8_t>& tailBytes = {},
  const std::vector<std::uint8_t>& changeMusicBytes = {},
  const std::vector<std::uint8_t>& changeMusicHelperBytes = {},
  const std::vector<std::uint8_t>& musicDatasetBytes = {},
  const std::vector<std::uint8_t>& musicPackPointerBytes = {},
  const std::vector<std::uint8_t>& romBytes = {},
  bool applyLoadSpc700DataStreams = false,
  const std::string& routineName = ""
) {
  CpuInstructionApuWriteProbe probe;
  std::vector<std::uint8_t> program = routineBytes.empty()
    ? (fullRoutine ? c0abbdFullProgram() : c0abbdPrefixProgram())
    : routineBytes;
  std::string selectedRoutineName = routineName.empty()
    ? (fullRoutine ? "full_C0ABBD_sep_sta_rep_rtl" : "sep_20_sta_002140_prefix_of_C0ABBD")
    : routineName;
  const bool ok = probe.run(command, fullRoutine, useJslCaller, useChangeMusicTail, useFullChangeMusic, preSatisfyChangeMusicPacks, applyLoadSpc700DataStreams, std::move(program), tailBytes, changeMusicBytes, changeMusicHelperBytes, musicDatasetBytes, musicPackPointerBytes, romBytes, selectedRoutineName);
  std::ostringstream loadArgs;
  loadArgs << "[";
  for (std::size_t index = 0; index < probe.loadSpc700DataStubArgs.size(); ++index) {
    const auto& item = probe.loadSpc700DataStubArgs[index];
    if (index) loadArgs << ",";
    loadArgs << "{\"a\":\"" << hexWord(item.first) << "\",\"x\":\"" << hexWord(item.second) << "\"}";
  }
  loadArgs << "]";
  std::ostringstream out;
  out << "{"
      << "\"ok\":" << (ok ? "true" : "false")
      << ",\"routine\":\"" << probe.routine << "\""
      << ",\"routine_bytes\":" << probe.programBytes.size()
      << ",\"call_through_jsl\":" << (probe.callThroughJsl ? "true" : "false")
      << ",\"call_through_change_music_tail\":" << (probe.callThroughChangeMusicTail ? "true" : "false")
      << ",\"call_through_full_change_music\":" << (probe.callThroughFullChangeMusic ? "true" : "false")
      << ",\"pre_satisfy_change_music_packs\":" << (probe.preSatisfyChangeMusicPacks ? "true" : "false")
      << ",\"change_music_tail_bytes\":" << probe.changeMusicTailBytes.size()
      << ",\"change_music_bytes\":" << probe.changeMusicBytes.size()
      << ",\"change_music_helper_bytes\":" << probe.changeMusicHelperBytes.size()
      << ",\"music_dataset_bytes\":" << probe.musicDatasetBytes.size()
      << ",\"music_pack_pointer_bytes\":" << probe.musicPackPointerBytes.size()
      << ",\"load_spc700_data_stub_calls\":" << probe.loadSpc700DataStubCalls
      << ",\"load_spc700_data_apply_streams\":" << (probe.applyLoadSpc700DataStreams ? "true" : "false")
      << ",\"load_spc700_data_applied_streams\":" << probe.loadSpc700DataAppliedStreams
      << ",\"load_spc700_data_applied_blocks\":" << probe.loadSpc700DataAppliedBlocks
      << ",\"load_spc700_data_applied_bytes\":" << probe.loadSpc700DataAppliedBytes
      << ",\"load_spc700_data_apply_errors\":" << probe.loadSpc700DataApplyErrors
      << ",\"last_load_spc700_data_a\":\"" << hexWord(probe.lastLoadSpc700DataA) << "\""
      << ",\"last_load_spc700_data_x\":\"" << hexWord(probe.lastLoadSpc700DataX) << "\""
      << ",\"load_spc700_data_stub_args\":" << loadArgs.str()
      << ",\"instruction_count\":" << probe.instructionCount
      << ",\"writes_to_2140\":" << probe.writesTo2140
      << ",\"last_write_address\":\"" << hexWord(static_cast<std::uint16_t>(probe.lastWriteAddress)) << "\""
      << ",\"last_write_data\":\"" << hexByte(probe.lastWriteData) << "\""
      << ",\"final_pc\":\"0x" << std::hex << std::uppercase << std::setw(6) << std::setfill('0') << probe.finalPc << "\""
      << "}";
  return out.str();
}

std::vector<std::uint8_t> buildSpcSnapshot(
  std::uint16_t pc,
  std::uint16_t ya,
  std::uint8_t x,
  std::uint8_t s,
  std::uint8_t p
) {
  auto& dsp = ares::SuperFamicom::dsp;
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
  std::copy(dsp.apuram, dsp.apuram + 65536, snapshot.begin() + 0x100);
  std::copy(dsp.registers, dsp.registers + 128, snapshot.begin() + 0x10100);
  return snapshot;
}

int main(int argc, char** argv) {
  try {
    const fs::path apuRamPath = argPath(argc, argv, "--apu-ram");
    if (apuRamPath.empty()) throw std::runtime_error("usage: earthbound_ares_smp_mailbox_smoke --apu-ram <path> [--command 0x2e] [--steps 200000] [--inject-on-pc-062a] [--inject-via-cpu-apu-write|--inject-via-cpu-instruction|--inject-via-cpu-routine|--inject-via-cpu-routine-file|--inject-via-cpu-routine-file-jsl]");
    const fs::path snapshotPath = argPath(argc, argv, "--snapshot-out");
    const fs::path cpuRoutineFile = argPath(argc, argv, "--cpu-routine-file");
    const fs::path cpuTailFile = argPath(argc, argv, "--cpu-tail-file");
    const fs::path changeMusicFile = argPath(argc, argv, "--change-music-file");
    const fs::path changeMusicHelperFile = argPath(argc, argv, "--change-music-helper-file");
    const fs::path musicDatasetFile = argPath(argc, argv, "--music-dataset-file");
    const fs::path musicPackPointerFile = argPath(argc, argv, "--music-pack-pointer-file");
    const fs::path romFile = argPath(argc, argv, "--rom-file");
    const int command = argInt(argc, argv, "--command", 0x2e);
    const int steps = argInt(argc, argv, "--steps", 200000);
    const bool injectOnCommandReadPc = hasFlag(argc, argv, "--inject-on-pc-062a");
    const bool injectViaCpuApuWrite = hasFlag(argc, argv, "--inject-via-cpu-apu-write");
    const bool injectViaCpuInstruction = hasFlag(argc, argv, "--inject-via-cpu-instruction");
    const bool injectViaCpuRoutine = hasFlag(argc, argv, "--inject-via-cpu-routine");
    const bool injectViaCpuRoutineFile = hasFlag(argc, argv, "--inject-via-cpu-routine-file");
    const bool injectViaCpuRoutineFileJsl = hasFlag(argc, argv, "--inject-via-cpu-routine-file-jsl");
    const bool injectViaChangeMusicTail = hasFlag(argc, argv, "--inject-via-change-music-tail");
    const bool injectViaFullChangeMusic = hasFlag(argc, argv, "--inject-via-full-change-music");
    const bool runFullChangeMusicLoadPath = hasFlag(argc, argv, "--full-change-music-run-load-path");
    const bool applyLoadSpc700DataStreams = hasFlag(argc, argv, "--apply-load-spc700-data-streams");
    if ((injectViaCpuApuWrite ? 1 : 0) + (injectViaCpuInstruction ? 1 : 0) + (injectViaCpuRoutine ? 1 : 0) + (injectViaCpuRoutineFile ? 1 : 0) + (injectViaCpuRoutineFileJsl ? 1 : 0) + (injectViaChangeMusicTail ? 1 : 0) + (injectViaFullChangeMusic ? 1 : 0) > 1) {
      throw std::runtime_error("choose only one CPU delivery mode");
    }
    std::vector<std::uint8_t> cpuRoutineBytes;
    if (injectViaCpuRoutineFile || injectViaCpuRoutineFileJsl || injectViaChangeMusicTail || injectViaFullChangeMusic) {
      if (cpuRoutineFile.empty()) throw std::runtime_error("ROM-derived CPU routine delivery requires --cpu-routine-file");
      cpuRoutineBytes = readBytes(cpuRoutineFile);
      if (cpuRoutineBytes.empty()) throw std::runtime_error("CPU routine fixture is empty");
    }
    std::vector<std::uint8_t> cpuTailBytes;
    if (injectViaChangeMusicTail) {
      if (cpuTailFile.empty()) throw std::runtime_error("--inject-via-change-music-tail requires --cpu-tail-file");
      cpuTailBytes = readBytes(cpuTailFile);
      if (cpuTailBytes.empty()) throw std::runtime_error("CPU tail fixture is empty");
    }
    std::vector<std::uint8_t> changeMusicBytes;
    if (injectViaFullChangeMusic) {
      if (changeMusicFile.empty()) throw std::runtime_error("--inject-via-full-change-music requires --change-music-file");
      changeMusicBytes = readBytes(changeMusicFile);
      if (changeMusicBytes.empty()) throw std::runtime_error("ChangeMusic fixture is empty");
    }
    std::vector<std::uint8_t> changeMusicHelperBytes;
    if (injectViaFullChangeMusic && runFullChangeMusicLoadPath) {
      if (changeMusicHelperFile.empty()) throw std::runtime_error("--full-change-music-run-load-path requires --change-music-helper-file");
      changeMusicHelperBytes = readBytes(changeMusicHelperFile);
      if (changeMusicHelperBytes.empty()) throw std::runtime_error("ChangeMusic helper fixture is empty");
    }
    std::vector<std::uint8_t> musicDatasetBytes;
    if (injectViaFullChangeMusic) {
      if (musicDatasetFile.empty()) throw std::runtime_error("--inject-via-full-change-music requires --music-dataset-file");
      musicDatasetBytes = readBytes(musicDatasetFile);
      if (musicDatasetBytes.empty()) throw std::runtime_error("MusicDatasetTable fixture is empty");
    }
    std::vector<std::uint8_t> musicPackPointerBytes;
    if (injectViaFullChangeMusic && runFullChangeMusicLoadPath) {
      if (musicPackPointerFile.empty()) throw std::runtime_error("--full-change-music-run-load-path requires --music-pack-pointer-file");
      musicPackPointerBytes = readBytes(musicPackPointerFile);
      if (musicPackPointerBytes.empty()) throw std::runtime_error("MusicPackPointerTable fixture is empty");
    }
    std::vector<std::uint8_t> romBytes;
    if (applyLoadSpc700DataStreams) {
      if (romFile.empty()) throw std::runtime_error("--apply-load-spc700-data-streams requires --rom-file");
      romBytes = readBytes(romFile);
      if (romBytes.empty()) throw std::runtime_error("ROM file is empty");
    }
    const std::vector<std::uint8_t> apuRam = readBytes(apuRamPath);
    if (apuRam.size() != 65536) throw std::runtime_error("APU RAM seed must be exactly 65536 bytes");

    auto& dsp = ares::SuperFamicom::dsp;
    auto& smp = ares::SuperFamicom::smp;
    auto& cpu = ares::SuperFamicom::cpu;
    std::copy(apuRam.begin(), apuRam.end(), dsp.apuram);

    // Avoid SMP::power(), which expects a loaded full SFC system pak for IPL.
    smp.SPC700::power();
    std::copy(apuRam.begin(), apuRam.end(), dsp.apuram);
    smp.r.pc.w = 0x0500;
    std::string cpuInstructionProbeJson;
    auto deliverCommand = [&]() {
      if (injectViaCpuInstruction || injectViaCpuRoutine || injectViaCpuRoutineFile || injectViaCpuRoutineFileJsl || injectViaChangeMusicTail || injectViaFullChangeMusic) {
        cpuInstructionProbeJson = runCpuInstructionApuWrite(
          static_cast<std::uint8_t>(command),
          injectViaCpuRoutine || injectViaCpuRoutineFile || injectViaCpuRoutineFileJsl,
          injectViaCpuRoutineFileJsl,
          injectViaChangeMusicTail,
          injectViaFullChangeMusic,
          !runFullChangeMusicLoadPath,
          cpuRoutineBytes,
          cpuTailBytes,
          changeMusicBytes,
          changeMusicHelperBytes,
          musicDatasetBytes,
          musicPackPointerBytes,
          romBytes,
          applyLoadSpc700DataStreams,
          injectViaFullChangeMusic ? (applyLoadSpc700DataStreams ? "rom_fixture_ChangeMusic_full_load_path_applied_loader" : (runFullChangeMusicLoadPath ? "rom_fixture_ChangeMusic_full_load_path_stubbed_loader" : "rom_fixture_ChangeMusic_full_presatisfied_packs")) : (injectViaChangeMusicTail ? "rom_fixture_ChangeMusic_tail_to_C0ABBD" : (injectViaCpuRoutineFileJsl ? "rom_fixture_C0ABBD_jsl_call_context" : (injectViaCpuRoutineFile ? "rom_fixture_C0ABBD_sep_sta_long_rep_rtl" : "")))
        );
      } else if (injectViaCpuApuWrite) {
        cpu.writeAPU(0x2140, static_cast<std::uint8_t>(command));
      } else {
        smp.portWrite(0, static_cast<std::uint8_t>(command));
      }
    };
    if (!injectOnCommandReadPc) {
      deliverCommand();
    }

    bool reachedCommandReadPc = false;
    bool reachedAckWriteShape = false;
    bool reachedKeyOn = false;
    bool injectedCommand = !injectOnCommandReadPc;
    int injectionStep = injectedCommand ? 0 : -1;
    int commandReadStep = -1;
    int zeroAckStep = -1;
    int keyOnStep = -1;
    std::uint8_t keyOnData = 0;
    std::vector<std::uint8_t> lastKeyOnSnapshot;
    std::uint16_t lastKeyOnPc = 0;
    std::uint16_t lastKeyOnYa = 0;
    std::uint8_t lastKeyOnX = 0;
    std::uint8_t lastKeyOnS = 0;
    std::uint8_t lastKeyOnP = 0;
    std::uint16_t finalPc = 0;
    for (int step = 0; step < steps; ++step) {
      const std::uint16_t pc = static_cast<std::uint16_t>(smp.r.pc.w);
      if (pc == 0x062a && !reachedCommandReadPc) {
        reachedCommandReadPc = true;
        commandReadStep = step;
      }
      if (pc == 0x062a && injectOnCommandReadPc && !injectedCommand) {
        deliverCommand();
        injectedCommand = true;
        injectionStep = step;
      }
      smp.instruction();
      finalPc = static_cast<std::uint16_t>(smp.r.pc.w);
      if (reachedCommandReadPc && !reachedAckWriteShape && static_cast<std::uint8_t>(smp.portRead(0)) == 0x00) {
        reachedAckWriteShape = true;
        zeroAckStep = step;
      }
      const std::uint8_t kon = static_cast<std::uint8_t>(dsp.registers[0x4c]);
      if (reachedAckWriteShape && kon && !reachedKeyOn) {
        reachedKeyOn = true;
        keyOnStep = step;
        keyOnData = kon;
        lastKeyOnPc = static_cast<std::uint16_t>(smp.r.pc.w);
        lastKeyOnYa = static_cast<std::uint16_t>(smp.r.ya.w);
        lastKeyOnX = static_cast<std::uint8_t>(smp.r.x);
        lastKeyOnS = static_cast<std::uint8_t>(smp.r.s);
        lastKeyOnP = static_cast<std::uint8_t>(static_cast<unsigned>(smp.r.p));
        lastKeyOnSnapshot = buildSpcSnapshot(lastKeyOnPc, lastKeyOnYa, lastKeyOnX, lastKeyOnS, lastKeyOnP);
        break;
      }
    }
    if (reachedKeyOn && !snapshotPath.empty()) {
      writeBytes(snapshotPath, lastKeyOnSnapshot);
    }

    std::cout << "{\n";
    std::cout << "  \"schema\": \"earthbound-decomp.ares-smp-mailbox-smoke.v1\",\n";
    std::cout << "  \"apu_ram_path\": \"" << jsonEscape(apuRamPath.string()) << "\",\n";
    std::cout << "  \"command\": \"" << hexByte(static_cast<std::uint8_t>(command)) << "\",\n";
    std::string deliveryMode;
    if (injectViaFullChangeMusic) {
      deliveryMode = injectOnCommandReadPc
        ? (applyLoadSpc700DataStreams ? "ares_wdc65816_full_change_music_load_apply_on_pc_062a" : (runFullChangeMusicLoadPath ? "ares_wdc65816_full_change_music_load_stub_on_pc_062a" : "ares_wdc65816_full_change_music_on_pc_062a"))
        : (applyLoadSpc700DataStreams ? "ares_wdc65816_full_change_music_load_apply_initial" : (runFullChangeMusicLoadPath ? "ares_wdc65816_full_change_music_load_stub_initial" : "ares_wdc65816_full_change_music_initial"));
    } else if (injectViaChangeMusicTail) {
      deliveryMode = injectOnCommandReadPc ? "ares_wdc65816_change_music_tail_on_pc_062a" : "ares_wdc65816_change_music_tail_initial";
    } else if (injectViaCpuRoutineFileJsl) {
      deliveryMode = injectOnCommandReadPc ? "ares_wdc65816_rom_c0abbd_jsl_on_pc_062a" : "ares_wdc65816_rom_c0abbd_jsl_initial";
    } else if (injectViaCpuRoutineFile) {
      deliveryMode = injectOnCommandReadPc ? "ares_wdc65816_rom_c0abbd_on_pc_062a" : "ares_wdc65816_rom_c0abbd_initial";
    } else if (injectViaCpuRoutine) {
      deliveryMode = injectOnCommandReadPc ? "ares_wdc65816_full_c0abbd_on_pc_062a" : "ares_wdc65816_full_c0abbd_initial";
    } else if (injectViaCpuInstruction) {
      deliveryMode = injectOnCommandReadPc ? "ares_wdc65816_sta_2140_on_pc_062a" : "ares_wdc65816_sta_2140_initial";
    } else if (injectViaCpuApuWrite) {
      deliveryMode = injectOnCommandReadPc ? "ares_cpu_writeapu_2140_on_pc_062a" : "ares_cpu_writeapu_2140_initial";
    } else {
      deliveryMode = injectOnCommandReadPc ? "ares_smp_portwrite_on_pc_062a" : "ares_smp_portwrite_initial";
    }
    std::cout << "  \"command_delivery_mode\": \"" << deliveryMode << "\",\n";
    if (injectViaCpuInstruction || injectViaCpuRoutine || injectViaCpuRoutineFile || injectViaCpuRoutineFileJsl || injectViaChangeMusicTail || injectViaFullChangeMusic) {
      std::cout << "  \"cpu_instruction_probe\": " << (cpuInstructionProbeJson.empty() ? "null" : cpuInstructionProbeJson) << ",\n";
    }
    std::cout << "  \"command_injected\": " << (injectedCommand ? "true" : "false") << ",\n";
    std::cout << "  \"command_injection_step\": " << injectionStep << ",\n";
    std::cout << "  \"steps_limit\": " << steps << ",\n";
    std::cout << "  \"final_pc\": \"" << hexWord(finalPc) << "\",\n";
    std::cout << "  \"reached_command_read_pc_062a\": " << (reachedCommandReadPc ? "true" : "false") << ",\n";
    std::cout << "  \"command_read_step\": " << commandReadStep << ",\n";
    std::cout << "  \"reached_zero_ack_shape\": " << (reachedAckWriteShape ? "true" : "false") << ",\n";
    std::cout << "  \"zero_ack_step\": " << zeroAckStep << ",\n";
    std::cout << "  \"reached_key_on_after_ack\": " << (reachedKeyOn ? "true" : "false") << ",\n";
    std::cout << "  \"key_on_step\": " << keyOnStep << ",\n";
    std::cout << "  \"key_on_data\": \"" << hexByte(keyOnData) << "\",\n";
    std::cout << "  \"last_key_on_snapshot\": {\n";
    std::cout << "    \"available\": " << (reachedKeyOn ? "true" : "false");
    if (reachedKeyOn) {
      std::cout << ",\n";
      std::cout << "    \"kind\": \"ares_smp_mailbox_last_keyon_spc_snapshot\",\n";
      std::cout << "    \"path\": \"" << jsonEscape(snapshotPath.string()) << "\",\n";
      std::cout << "    \"bytes\": " << lastKeyOnSnapshot.size() << ",\n";
      std::cout << "    \"pc\": \"" << hexWord(lastKeyOnPc) << "\",\n";
      std::cout << "    \"registers\": {\"ya\": \"" << hexWord(lastKeyOnYa) << "\", \"x\": \"" << hexByte(lastKeyOnX) << "\", \"s\": \"" << hexByte(lastKeyOnS) << "\", \"p\": \"" << hexByte(lastKeyOnP) << "\"},\n";
      std::cout << "    \"key_on_data\": \"" << hexByte(keyOnData) << "\"\n";
    } else {
      std::cout << "\n";
    }
    std::cout << "  }\n";
    std::cout << "}\n";
    return reachedCommandReadPc && reachedAckWriteShape && reachedKeyOn ? 0 : 2;
  } catch (const std::exception& error) {
    std::cerr << "ares SMP mailbox smoke failed: " << error.what() << "\n";
    return 1;
  }
}
