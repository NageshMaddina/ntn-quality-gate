*** Settings ***
Documentation    Behaviour on a degraded satellite link (rain fade, blockage).
Resource         common.resource
Suite Setup      Prepare Degraded Suite

*** Variables ***
${SOS_COUNT}    40

*** Test Cases ***
SOS Delivery Holds Under Heavy Packet Loss
    [Tags]    REQ-SOS-01    critical    kpi
    Set Link    loss_pct=70    seed=11
    ${delivered}=    Set Variable    ${0}
    FOR    ${i}    IN RANGE    ${SOS_COUNT}
        ${resp}=    Send Message    ${DEVICE}    text=SOS hiker injured    sos=${True}
        IF    ${resp.status_code} == 200
            ${delivered}=    Evaluate    ${delivered} + 1
        END
    END
    ${pct}=    Evaluate    round(100 * ${delivered} / ${SOS_COUNT}, 1)
    Record Kpi    sos_delivery_pct_at_70_loss    ${pct}
    Log    SOS delivery at 70% loss: ${pct}%
    Should Be True    ${pct} >= 90    SOS delivery ${pct}% is below the 90% requirement

Failed Delivery Is Reported Explicitly
    [Tags]    REQ-LNK-01    critical
    Set Link    loss_pct=100
    ${resp}=    Send Message    ${DEVICE}    expected_status=504
    Should Be Equal    ${resp.json()}[detail][status]    FAILED
    Should Be Equal As Integers    ${resp.json()}[detail][attempts]    ${resp.json()}[detail][budget]

*** Keywords ***
Prepare Degraded Suite
    Open Lab Session
    ${imsi}=    Make Imsi    3
    Register Device    ${imsi}
    Set Suite Variable    ${DEVICE}    ${imsi}
