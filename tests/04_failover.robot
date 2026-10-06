*** Settings ***
Documentation    Ground gateway failure and recovery.
Resource         common.resource
Suite Setup      Prepare Failover Suite

*** Test Cases ***
Primary Gateway Loss Fails Over Without Interruption
    [Tags]    REQ-FO-01    critical
    POST On Session    sat    /admin/gateways/gw-primary/fail
    ${resp}=    Send Message    ${DEVICE}    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    200    Service interrupted after primary gateway loss
    Should Be Equal    ${resp.json()}[gateway]    gw-secondary
    [Teardown]    POST On Session    sat    /admin/gateways/gw-primary/restore

Total Outage Returns 503 And Recovers
    [Tags]    REQ-FO-02    critical
    POST On Session    sat    /admin/gateways/gw-primary/fail
    POST On Session    sat    /admin/gateways/gw-secondary/fail
    ${imsi}=    Make Imsi    5
    Register Device    ${imsi}    expected_status=503
    POST On Session    sat    /admin/gateways/gw-primary/restore
    ${resp}=    Register Device    ${imsi}
    Should Be Equal    ${resp.json()}[state]    REGISTERED
    [Teardown]    POST On Session    sat    /admin/gateways/gw-secondary/restore

*** Keywords ***
Prepare Failover Suite
    Open Lab Session
    ${imsi}=    Make Imsi    4
    Register Device    ${imsi}
    Set Suite Variable    ${DEVICE}    ${imsi}
