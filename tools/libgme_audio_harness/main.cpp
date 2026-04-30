#include <gme.h>

#include <array>
#include <cmath>
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
    while (bufferSize != 56) update(&zero, 1);
    std::array<std::uint8_t, 8> lengthBytes{};
    for (int i = 7; i >= 0; --i) {
      lengthBytes[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>(bitLength >> ((7 - i) * 8));
    }
    update(lengthBytes.data(), lengthBytes.size());

    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (auto word : {h0, h1, h2, h3, h4}) out << std::setw(8) << word;
    return out.str();
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

std::string sha1Hex(const std::vector<std::uint8_t>& data) {
  Sha1 sha1;
  sha1.update(data.data(), data.size());
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

double extractNumberField(const std::string& json, const std::string& field, std::size_t start = 0) {
  const std::string key = "\"" + field + "\"";
  const std::size_t keyPos = json.find(key, start);
  if (keyPos == std::string::npos) throw std::runtime_error("missing JSON field: " + field);
  const std::size_t colon = json.find(':', keyPos + key.size());
  if (colon == std::string::npos) throw std::runtime_error("malformed JSON number field: " + field);
  const std::size_t first = json.find_first_of("-0123456789", colon + 1);
  if (first == std::string::npos) throw std::runtime_error("missing JSON number value: " + field);
  const std::size_t last = json.find_first_not_of("0123456789.eE+-", first);
  return std::stod(json.substr(first, last - first));
}

fs::path argValue(int argc, char** argv, const std::string& name) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == name) return fs::path(argv[i + 1]);
  }
  return {};
}

std::string findSnapshotPathForTrack(const std::string& indexJson, int trackId) {
  std::size_t pos = 0;
  while (true) {
    const std::size_t trackPos = indexJson.find("\"track_id\"", pos);
    if (trackPos == std::string::npos) break;
    const int foundTrack = extractIntField(indexJson, "track_id", trackPos);
    const std::size_t snapshotPos = indexJson.find("\"snapshot\"", trackPos);
    if (snapshotPos == std::string::npos) break;
    if (foundTrack == trackId) {
      return extractStringField(indexJson, "path", snapshotPos);
    }
    pos = snapshotPos + 10;
  }
  throw std::runtime_error("snapshot path not found for track");
}

void writeWav(const fs::path& path, const std::vector<short>& samples, int sampleRate, int channels) {
  fs::create_directories(path.parent_path());
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("could not write " + path.string());
  const std::uint32_t dataBytes = static_cast<std::uint32_t>(samples.size() * sizeof(short));
  const std::uint32_t riffBytes = 36 + dataBytes;
  const std::uint32_t byteRate = static_cast<std::uint32_t>(sampleRate * channels * sizeof(short));
  const std::uint16_t blockAlign = static_cast<std::uint16_t>(channels * sizeof(short));
  auto u16 = [&](std::uint16_t value) {
    out.put(static_cast<char>(value & 0xff));
    out.put(static_cast<char>((value >> 8) & 0xff));
  };
  auto u32 = [&](std::uint32_t value) {
    out.put(static_cast<char>(value & 0xff));
    out.put(static_cast<char>((value >> 8) & 0xff));
    out.put(static_cast<char>((value >> 16) & 0xff));
    out.put(static_cast<char>((value >> 24) & 0xff));
  };
  out.write("RIFF", 4);
  u32(riffBytes);
  out.write("WAVEfmt ", 8);
  u32(16);
  u16(1);
  u16(static_cast<std::uint16_t>(channels));
  u32(static_cast<std::uint32_t>(sampleRate));
  u32(byteRate);
  u16(blockAlign);
  u16(16);
  out.write("data", 4);
  u32(dataBytes);
  out.write(reinterpret_cast<const char*>(samples.data()), static_cast<std::streamsize>(dataBytes));
}

int main(int argc, char** argv) {
  try {
    const fs::path jobPath = argValue(argc, argv, "--job");
    if (jobPath.empty()) {
      std::cerr << "usage: earthbound_libgme_audio_harness --job <job.json> [--result <result.json>] [--snapshot-index <index.json>]\n";
      return 2;
    }
    fs::path resultPath = argValue(argc, argv, "--result");
    fs::path snapshotIndexPath = argValue(argc, argv, "--snapshot-index");
    if (snapshotIndexPath.empty()) {
      snapshotIndexPath = fs::path("build/audio/backend-jobs/diagnostic-spc-snapshots.json");
    }

    const std::string jobJson = readText(jobPath);
    const int trackId = extractIntField(jobJson, "track_id");
    const std::string jobId = extractStringField(jobJson, "job_id");
    const std::string backendId = extractStringField(jobJson, "backend_id");
    const std::string fixturePath = extractStringField(jobJson, "fixture_path");
    const std::string inputApuRamSha1 = extractStringField(jobJson, "input_apu_ram_sha1");
    const std::string outputDir = extractStringField(jobJson, "output_dir");
    const std::string trackName = extractStringField(jobJson, "track_name");
    if (resultPath.empty()) resultPath = fs::path(extractStringField(jobJson, "result_path"));
    resultPath = fs::absolute(resultPath);

    const std::string snapshotIndexJson = readText(snapshotIndexPath);
    const fs::path spcPath = findSnapshotPathForTrack(snapshotIndexJson, trackId);
    const std::vector<std::uint8_t> spcBytes = readBytes(spcPath);
    if (!std::string_view(reinterpret_cast<const char*>(spcBytes.data()), std::min<std::size_t>(spcBytes.size(), 32)).starts_with("SNES-SPC700 Sound File Data")) {
      throw std::runtime_error("input SPC is missing SNES-SPC700 signature");
    }

    const std::size_t renderOptionsPos = jobJson.find("\"render_options\"");
    const int sampleRate = extractIntField(jobJson, "sample_rate", renderOptionsPos);
    const int channels = extractIntField(jobJson, "channels", renderOptionsPos);
    const double seconds = extractNumberField(jobJson, "seconds", renderOptionsPos);
    const std::string outputFormat = extractStringField(jobJson, "output_format", renderOptionsPos);
    if (sampleRate <= 0 || sampleRate > 192000) throw std::runtime_error("invalid sample_rate");
    if (channels != 2) throw std::runtime_error("libgme harness currently supports stereo jobs only");
    if (seconds <= 0.0 || seconds > 600.0) throw std::runtime_error("invalid render seconds");
    if (outputFormat != "wav") throw std::runtime_error("libgme harness currently supports wav output only");
    const int sampleCount = static_cast<int>(std::llround(static_cast<long double>(sampleRate) * static_cast<long double>(channels) * static_cast<long double>(seconds)));
    Music_Emu* emu = nullptr;
    if (const char* error = gme_open_file(spcPath.string().c_str(), &emu, sampleRate)) {
      throw std::runtime_error(std::string("gme_open_file failed: ") + error);
    }
    if (const char* error = gme_start_track(emu, 0)) {
      gme_delete(emu);
      throw std::runtime_error(std::string("gme_start_track failed: ") + error);
    }
    gme_ignore_silence(emu, 1);
    gme_enable_accuracy(emu, 1);

    std::vector<short> samples(static_cast<std::size_t>(sampleCount));
    if (const char* error = gme_play(emu, sampleCount, samples.data())) {
      gme_delete(emu);
      throw std::runtime_error(std::string("gme_play failed: ") + error);
    }
    const int voiceCount = gme_voice_count(emu);
    const char* warning = gme_warning(emu);
    gme_delete(emu);

    const fs::path outputRoot = fs::absolute(outputDir);
    const fs::path wavPath = outputRoot / "diagnostic-libgme-render.wav";
    writeWav(wavPath, samples, sampleRate, channels);
    const std::vector<std::uint8_t> wavBytes = readBytes(wavPath);

    long long absoluteSampleSum = 0;
    long double squareSampleSum = 0.0;
    std::size_t nonzeroSampleCount = 0;
    std::size_t firstNonzeroSample = samples.size();
    std::size_t lastNonzeroSample = 0;
    short peak = 0;
    for (std::size_t i = 0; i < samples.size(); ++i) {
      const short sample = samples[i];
      const int value = sample < 0 ? -static_cast<int>(sample) : static_cast<int>(sample);
      absoluteSampleSum += value;
      squareSampleSum += static_cast<long double>(sample) * static_cast<long double>(sample);
      if (sample != 0) {
        ++nonzeroSampleCount;
        if (firstNonzeroSample == samples.size()) firstNonzeroSample = i;
        lastNonzeroSample = i;
      }
      if (value > peak) peak = static_cast<short>(value);
    }
    const long double rms = samples.empty() ? 0.0 : std::sqrt(squareSampleSum / static_cast<long double>(samples.size()));

    std::ostringstream renderHash;
    renderHash << "{\n";
    renderHash << "  \"schema\": \"earthbound-decomp.libgme-render-hash.v1\",\n";
    renderHash << "  \"job_id\": \"" << jsonEscape(jobId) << "\",\n";
    renderHash << "  \"track_id\": " << trackId << ",\n";
    renderHash << "  \"track_name\": \"" << jsonEscape(trackName) << "\",\n";
    renderHash << "  \"source_spc_path\": \"" << jsonEscape(spcPath.string()) << "\",\n";
    renderHash << "  \"source_spc_sha1\": \"" << sha1Hex(spcBytes) << "\",\n";
    renderHash << "  \"sample_rate\": " << sampleRate << ",\n";
    renderHash << "  \"channels\": " << channels << ",\n";
    renderHash << "  \"seconds\": " << std::fixed << std::setprecision(3) << seconds << ",\n";
    renderHash << "  \"rendered_samples\": " << samples.size() << ",\n";
    renderHash << "  \"voice_count\": " << voiceCount << ",\n";
    renderHash << "  \"peak_abs_sample\": " << peak << ",\n";
    renderHash << "  \"sum_abs_samples\": " << absoluteSampleSum << ",\n";
    renderHash << "  \"nonzero_sample_count\": " << nonzeroSampleCount << ",\n";
    renderHash << "  \"first_nonzero_sample_index\": " << (firstNonzeroSample == samples.size() ? -1 : static_cast<long long>(firstNonzeroSample)) << ",\n";
    renderHash << "  \"last_nonzero_sample_index\": " << (nonzeroSampleCount ? static_cast<long long>(lastNonzeroSample) : -1) << ",\n";
    renderHash << "  \"rms_sample\": " << std::fixed << std::setprecision(6) << static_cast<double>(rms) << ",\n";
    renderHash << "  \"warning\": \"" << jsonEscape(warning ? warning : "") << "\",\n";
    renderHash << "  \"faithfulness\": \"diagnostic_input_snapshot_not_runtime_faithful\"\n";
    renderHash << "}\n";
    const fs::path renderHashPath = outputRoot / "libgme-render-hash.json";
    writeText(renderHashPath, renderHash.str());
    const std::vector<std::uint8_t> renderHashBytes = readBytes(renderHashPath);

    std::ostringstream result;
    result << "{\n";
    result << "  \"schema\": \"earthbound-decomp.audio-backend-result.v1\",\n";
    result << "  \"job_id\": \"" << jsonEscape(jobId) << "\",\n";
    result << "  \"backend_id\": \"" << jsonEscape(backendId) << "\",\n";
    result << "  \"backend_version\": \"libgme-spc-diagnostic-renderer-0.1\",\n";
    result << "  \"status\": \"ok\",\n";
    result << "  \"input_fixture_path\": \"" << jsonEscape(fixturePath) << "\",\n";
    result << "  \"input_apu_ram_sha1\": \"" << jsonEscape(inputApuRamSha1) << "\",\n";
    result << "  \"outputs\": [\n";
    result << "    {\"kind\": \"complete_spc_snapshot\", \"path\": \"" << jsonEscape(spcPath.string()) << "\", \"bytes\": " << spcBytes.size() << ", \"sha1\": \"" << sha1Hex(spcBytes) << "\"},\n";
    result << "    {\"kind\": \"rendered_wav\", \"path\": \"" << jsonEscape(wavPath.string()) << "\", \"bytes\": " << wavBytes.size() << ", \"sha1\": \"" << sha1Hex(wavBytes) << "\"},\n";
    result << "    {\"kind\": \"render_hash_json\", \"path\": \"" << jsonEscape(renderHashPath.string()) << "\", \"bytes\": " << renderHashBytes.size() << ", \"sha1\": \"" << sha1Hex(renderHashBytes) << "\"}\n";
    result << "  ],\n";
    result << "  \"diagnostics\": {\n";
    result << "    \"execution_mode\": \"libgme_spc_render_from_diagnostic_snapshot\",\n";
    result << "    \"handshake_policy\": \"inherits_diagnostic_ares_snapshot_preseed\",\n";
    result << "    \"timing_basis\": \"libgme_render_job_options_from_spc_header_state\",\n";
    result << "    \"message\": \"Rendered WAV through libgme from a diagnostic SPC snapshot. This proves the lightweight renderer path, not final runtime faithfulness.\"\n";
    result << "  }\n";
    result << "}\n";
    writeText(resultPath, result.str());
    std::cout << "Wrote libgme diagnostic renderer result -> " << resultPath.string() << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "libgme audio harness failed: " << error.what() << "\n";
    return 1;
  }
}
