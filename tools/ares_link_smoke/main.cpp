#include <sfc/sfc.hpp>

#include <cstdint>
#include <iostream>

int main() {
  auto& dsp = ares::SuperFamicom::dsp;
  volatile std::uint8_t firstByte = static_cast<std::uint8_t>(dsp.apuram[0]);
  std::cout << "ares SFC DSP link smoke OK; apuram[0]=" << static_cast<unsigned>(firstByte) << "\n";
  return 0;
}
