*** Settings ***
Documentation    Device registration (attach) over the satellite link.
Resource         common.resource
Suite Setup      Open Lab Session

*** Test Cases ***
Valid IMSI Registers Over GEO Link
    [Tags]    REQ-ATT-01    critical    smoke
    ${imsi}=    Make Imsi    1
    ${resp}=    Register Device    ${imsi}
    Should Be Equal    ${resp.json()}[state]    REGISTERED
    # A GEO round trip is ~540 ms, so attach can never be faster than that.
    Should Be True    ${resp.json()}[latency_ms] >= 480

Invalid IMSI Is Rejected
    [Tags]    REQ-ATT-02    critical
    Register Device    12345    expected_status=422
    Register Device    00101ABCDEFGHIJ    expected_status=422
