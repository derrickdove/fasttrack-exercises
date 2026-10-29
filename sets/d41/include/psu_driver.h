#pragma once

#include <string>

// A PSU is a power supply unit; this driver only formats and parses text.
struct ErrorReply {
    int code;
    std::string message;
};

std::string formatSetVoltage(double volts);
ErrorReply parseErrorReply(const std::string& reply);
double clampCurrent(double requestedAmps, double limitAmps);

// A session is an already-open instrument connection. Tests supply a fake.
class Session {
public:
    virtual ~Session() = default;
    virtual void close() = 0; // May throw when a cable has been disconnected.
};

class PsuDriver {
public:
    // Borrow the session: its owner must keep it alive until this driver is gone.
    explicit PsuDriver(Session* session) noexcept;
    ~PsuDriver() noexcept;
    PsuDriver(const PsuDriver&) = delete;
    PsuDriver& operator=(const PsuDriver&) = delete;

private:
    Session* session_;
};
