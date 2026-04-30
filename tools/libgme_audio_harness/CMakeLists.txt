cmake_minimum_required(VERSION 3.28)
project(earthbound_libgme_audio_harness LANGUAGES CXX)

set(LIBGME_ROOT "" CACHE PATH "Local libgme source checkout")
if(NOT LIBGME_ROOT)
  message(FATAL_ERROR "Set LIBGME_ROOT to the local game-music-emu checkout path")
endif()

set(LIBGME_BUILD "${LIBGME_ROOT}/build_msvc" CACHE PATH "Local libgme build directory")

add_executable(earthbound_libgme_audio_harness main.cpp)
target_compile_features(earthbound_libgme_audio_harness PRIVATE cxx_std_20)
target_include_directories(
  earthbound_libgme_audio_harness
  PRIVATE
    "${LIBGME_ROOT}/gme"
)
target_link_libraries(
  earthbound_libgme_audio_harness
  PRIVATE
    "${LIBGME_BUILD}/gme/RelWithDebInfo/gme.lib"
)
