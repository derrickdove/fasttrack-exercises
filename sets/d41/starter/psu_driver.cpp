#include "psu_driver.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <locale>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {
// Supplied: produce a command with a decimal point regardless of OS locale.
std::string voltageCommand(double volts) {
    std::ostringstream command;
    command.imbue(std::locale::classic());
    command << "VOLT " << std::fixed << std::setprecision(3)
            << (volts == 0.0 ? 0.0 : volts) << '\n';
    return command.str();
}
// Supplied for E2: remove only surrounding ASCII whitespace; all-whitespace
// input becomes an empty string. The message inside quotes is never trimmed.
[[maybe_unused]] std::string trimAscii(const std::string& text) {
    const auto first = text.find_first_not_of(" \t\r\n\v\f");
    if (first == std::string::npos) {
        return "";
    }
    const auto last = text.find_last_not_of(" \t\r\n\v\f");
    return text.substr(first, last - first + 1);
}

// Supplied for E2: accept exactly an optional sign and ASCII digits, fitting int.
// Bad spelling (including spaces or trailing text) and overflow both throw
// std::invalid_argument. Leading zeroes are allowed. No catch is needed in E2.
[[maybe_unused]] int toInt(const std::string& text) {
    const auto firstDigit = !text.empty() && (text.front() == '+' || text.front() == '-') ? 1U : 0U;
    if (text.size() == firstDigit ||
        text.find_first_not_of("0123456789", firstDigit) != std::string::npos) {
        throw std::invalid_argument("expected a signed decimal integer");
    }
    try {
        return std::stoi(text);
    } catch (const std::out_of_range&) {
        throw std::invalid_argument("integer does not fit int");
    }
}
} // namespace

std::string formatSetVoltage(double volts) {
    // E1: The station accepts unsafe voltages. Fix this range check.
    if (volts < 0.0 && volts > 30.0) {
        throw std::invalid_argument("voltage outside 0..30 V");
    }
    return voltageCommand(volts);
}

ErrorReply parseErrorReply(const std::string& /*reply*/) {
    throw std::logic_error("NotImplementedError: E2: parse one error reply");
}

double clampCurrent(double /*requestedAmps*/, double /*limitAmps*/) {
    throw std::logic_error("NotImplementedError: E3: clamp the requested current");
}

PsuDriver::PsuDriver(Session* session) noexcept : session_(session) {}

PsuDriver::~PsuDriver() noexcept {
    // E4: Teardown is missing. Close a present session without letting errors escape.
}
