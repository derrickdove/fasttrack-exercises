#include "doctest.h"
#include "psu_driver.h"

#include <limits>
#include <stdexcept>
#include <type_traits>

TEST_CASE("E1 format normal station voltage commands") {
    CHECK(formatSetVoltage(12.5) == "VOLT 12.500\n");
    CHECK(formatSetVoltage(3.125) == "VOLT 3.125\n");
    CHECK(formatSetVoltage(2.25) == "VOLT 2.250\n");
}

TEST_CASE("E1 include both supply voltage endpoints") {
    CHECK(formatSetVoltage(0.0) == "VOLT 0.000\n");
    CHECK(formatSetVoltage(-0.0) == "VOLT 0.000\n");
    CHECK(formatSetVoltage(30.0) == "VOLT 30.000\n");
}

TEST_CASE("E1 reject unsafe and nonfinite station setpoints") {
    for (double volts : {-0.001, 30.001, -100.0, 100.0,
                         std::numeric_limits<double>::infinity(),
                         -std::numeric_limits<double>::infinity(),
                         std::numeric_limits<double>::quiet_NaN()}) {
        CAPTURE(volts);
        CHECK_THROWS_AS(formatSetVoltage(volts), std::invalid_argument);
    }
}

TEST_CASE("E2 parse station faults and the no-error reply") {
    const auto fault = parseErrorReply("-113,\"Undefined header\"");
    CHECK(fault.code == -113);
    CHECK(fault.message == "Undefined header");
    const auto clean = parseErrorReply(" \t+0,\"No error\"\r\n");
    CHECK(clean.code == 0);
    CHECK(clean.message == "No error");
    const auto empty = parseErrorReply("000,\"\"");
    CHECK(empty.code == 0);
    CHECK(empty.message.empty());
    const auto warning = parseErrorReply("+17,\"fan warning\"");
    CHECK(warning.code == 17);
    CHECK(warning.message == "fan warning");
}

TEST_CASE("E2 preserve fault message text and comma characters") {
    const auto reply = parseErrorReply("\v\f12,\" CH1,\tC:\\logs, overload \"\t");
    CHECK(reply.code == 12);
    CHECK(reply.message == " CH1,\tC:\\logs, overload ");
    const auto negative = parseErrorReply("-0007,\"limit\"");
    CHECK(negative.code == -7);
    const auto padded = parseErrorReply("+00000000000000000000000000000017,\"padded\"");
    CHECK(padded.code == 17);
    CHECK(padded.message == "padded");
}

TEST_CASE("E2 reject malformed supply error reply grammar") {
    CHECK_THROWS_AS(parseErrorReply(" \t\r\n\v\f"), std::invalid_argument);
    for (const std::string reply : {"", " ", "-113", "1,no quotes", "1, 'bad'",
            "1, \"bad\"", "1 ,\"bad\"", "+ 1,\"bad\"", "1.0,\"bad\"",
            "--1,\"bad\"", "+-1,\"bad\"", "-+1,\"bad\"", "1\t2,\"bad\"",
            "+,\"bad\"", "-,\"bad\"", ",\"bad\"", " ,\"bad\"",
            "0x1,\"bad\"", "1e2,\"bad\"", "\xD9\xA1,\"bad\"",
            "1,\"bad\"tail", "1,\"bad\"\"", "1,\"bad\nline\"",
            "1,\"bad\rline\"", "1,\"unclosed", "1,\"a\\\"b\""}) {
        CAPTURE(reply);
        CHECK_THROWS_AS(parseErrorReply(reply), std::invalid_argument);
    }
}

TEST_CASE("E2 enforce the driver integer code range") {
    const auto maximum = parseErrorReply(std::to_string(std::numeric_limits<int>::max()) + ",\"max\"");
    CHECK(maximum.code == std::numeric_limits<int>::max());
    const auto minimum = parseErrorReply(std::to_string(std::numeric_limits<int>::min()) + ",\"min\"");
    CHECK(minimum.code == std::numeric_limits<int>::min());
    CHECK_THROWS_AS(parseErrorReply("99999999999999999999,\"overflow\""), std::invalid_argument);
    CHECK_THROWS_AS(parseErrorReply("-99999999999999999999,\"overflow\""), std::invalid_argument);
}

TEST_CASE("E3 limit operator current requests") {
    CHECK(clampCurrent(1.25, 3.0) == 1.25);
    CHECK(clampCurrent(-0.5, 3.0) == 0.0);
    CHECK(clampCurrent(7.0, 3.0) == 3.0);
}

TEST_CASE("E3 include current endpoints and a zero limit") {
    CHECK(clampCurrent(0.0, 3.0) == 0.0);
    CHECK(clampCurrent(3.0, 3.0) == 3.0);
    CHECK(clampCurrent(1.0, 0.0) == 0.0);
    CHECK(clampCurrent(-1.0, 0.0) == 0.0);
}

TEST_CASE("E3 reject invalid limits and nonfinite current values") {
    CHECK_THROWS_AS(clampCurrent(1.0, -0.01), std::invalid_argument);
    for (double bad : {std::numeric_limits<double>::infinity(),
                       -std::numeric_limits<double>::infinity(),
                       std::numeric_limits<double>::quiet_NaN()}) {
        CAPTURE(bad);
        CHECK_THROWS_AS(clampCurrent(bad, 3.0), std::invalid_argument);
        CHECK_THROWS_AS(clampCurrent(1.0, bad), std::invalid_argument);
    }
}

namespace {
class FakeSession : public Session {
public:
    int closes = 0;
    int failure = 0;
    void close() override {
        ++closes;
        if (failure == 1) { throw std::runtime_error("cable disconnected"); }
        if (failure == 2) { throw 7; } // Not every library throws std::exception.
    }
};
} // namespace

TEST_CASE("E4 close the borrowed instrument session exactly once") {
    FakeSession session;
    {
        PsuDriver driver(&session);
        CHECK(session.closes == 0);
    }
    CHECK_MESSAGE(session.closes == 1, "scope exit must close the instrument session once");
    // The caller still owns and can use session after the driver has gone.
    session.close();
    CHECK(session.closes == 2);
    CHECK_FALSE(std::is_copy_constructible<PsuDriver>::value);
}

TEST_CASE("E4 tolerate a missing instrument session") {
    CHECK(std::is_nothrow_destructible<PsuDriver>::value);
    { PsuDriver driver(nullptr); }
    CHECK(true); // Reaching here proves null did not crash.
}

TEST_CASE("E4 contain every session close exception") {
    for (int failure : {1, 2}) {
        FakeSession session;
        session.failure = failure;
        { PsuDriver driver(&session); }
        CHECK_MESSAGE(session.closes == 1, "even a failing close must be attempted exactly once");
    }
}

TEST_CASE("E4 preserve the original station failure during stack unwinding") {
    FakeSession session;
    session.failure = 1;
    try {
        PsuDriver driver(&session);
        throw std::runtime_error("measurement failed");
    } catch (const std::runtime_error& error) {
        CHECK(std::string(error.what()) == "measurement failed");
    }
    CHECK(session.closes == 1);
}
