*** Settings ***
Documentation    SMS over satellite: delivery, admission rules and latency.
Resource         common.resource
Suite Setup      Prepare Messaging Suite

*** Variables ***
${SAMPLES}    20

*** Test Cases ***
Registered Device Delivers SMS
    [Tags]    REQ-SMS-01    critical    smoke
    ${resp}=    Send Message    ${DEVICE}    expected_status=200
    Should Be Equal    ${resp.json()}[status]    DELIVERED

Unregistered Device Is Blocked
    [Tags]    REQ-SMS-02    critical
    ${stranger}=    Make Imsi    999
    Send Message    ${stranger}    expected_status=403

Oversized Message Is Rejected
    [Tags]    REQ-SMS-03
    ${long}=    Evaluate    "x" * 161
    Send Message    ${DEVICE}    text=${long}    expected_status=422

SMS p95 Latency Within Budget On Clean Link
    [Tags]    REQ-SMS-04    critical    kpi
    @{lat}=    Create List
    FOR    ${i}    IN RANGE    ${SAMPLES}
        ${resp}=    Send Message    ${DEVICE}    expected_status=200
        Append To List    ${lat}    ${resp.json()}[latency_ms]
    END
    ${p95}=    P95 Of    ${lat}
    Record Kpi    sms_p95_latency_ms    ${p95}
    Log    SMS p95 latency: ${p95} ms over ${SAMPLES} messages
    Should Be True    ${p95} < 1500    p95 latency ${p95} ms exceeds 1500 ms budget

Metrics Expose Delivery And Link State
    [Tags]    REQ-OBS-01
    ${resp}=    GET On Session    sat    /metrics
    Dictionary Should Contain Key    ${resp.json()}    sms_delivered
    Dictionary Should Contain Key    ${resp.json()}    sms_p95_latency_ms
    Should Be True    ${resp.json()}[sms_delivered] >= ${SAMPLES}

*** Keywords ***
Prepare Messaging Suite
    Open Lab Session
    ${imsi}=    Make Imsi    2
    Register Device    ${imsi}
    Set Suite Variable    ${DEVICE}    ${imsi}
