#pragma once
// ConveyorControl.h - HTTP client helpers for Flask conveyor API (ANSI/MBCS)
// Endpoints on the Flask server:
//   GET /health
//   GET /api/conveyor/start
//   GET /api/conveyor/stop
//   GET /api/conveyor/pulse?ms=2000
//   (optional) GET /api/conveyor/status
//
// Usage in your View/Dialog:
//   #include "ConveyorControl.h"
//   Conveyor_SetServerA("192.168.0.87", 8000); // Flask server IP:port
//   Conveyor_Start();                           // continuous run
//   Conveyor_Stop();                            // stop
//   Conveyor_PulseMS(2000);                     // 2s pulse
//
// If you prefer compile-time defaults, set these in Preprocessor Definitions:
//   CONVEYOR_SERVER_HOST="192.168.0.87"; CONVEYOR_SERVER_PORT=8000
// or just edit the defaults below.

#include <windows.h>
#include <string>

#ifndef CONVEYOR_SERVER_HOST
#define CONVEYOR_SERVER_HOST "192.168.0.87"  // Flask server IP (ANSI)
#endif

#ifndef CONVEYOR_SERVER_PORT
#define CONVEYOR_SERVER_PORT 8000            // Flask server port
#endif

// Global runtime configuration
void Conveyor_SetServerA(const char* host, unsigned short port);
void Conveyor_GetServerA(std::string& hostOut, unsigned short& portOut);

// Low-level (explicit host/port)
BOOL Conveyor_HealthA(const char* host, unsigned short port);
BOOL Conveyor_StartA(const char* host, unsigned short port, const char* dir /*"forward"|"backward"*/ = "forward");
BOOL Conveyor_StopA(const char* host, unsigned short port);
BOOL Conveyor_PulseMSA(const char* host, unsigned short port, int ms, const char* dir /*"forward"|"backward"*/ = "forward");
// Optional endpoints if you later add cycle control on the server:
BOOL Conveyor_CycleStartA(const char* host, unsigned short port, int run_ms, int stop_ms, const char* dir = "forward");
BOOL Conveyor_CycleStopA(const char* host, unsigned short port);

// Convenience wrappers using current global server (set via Conveyor_SetServerA)
BOOL Conveyor_Health();
BOOL Conveyor_Start(const char* dir = "forward");
BOOL Conveyor_Stop();
BOOL Conveyor_PulseMS(int ms, const char* dir = "forward");
BOOL Conveyor_CycleStart(int run_ms, int stop_ms, const char* dir = "forward");
BOOL Conveyor_CycleStop();

// Debug helper (shows current server)
void Conveyor_DebugShowConfigA();

