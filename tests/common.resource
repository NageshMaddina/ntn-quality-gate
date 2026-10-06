*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    SatLib.py

*** Variables ***
${BASE_URL}    http://127.0.0.1:8000

*** Keywords ***
Open Lab Session
    Create Session    sat    ${BASE_URL}    timeout=30
    Reset Lab

Reset Lab
    POST On Session    sat    /admin/reset

Set Link
    [Arguments]    ${loss_pct}=0    ${delay_ms}=270    ${jitter_ms}=20    ${seed}=42
    ${body}=    Create Dictionary    loss_pct=${loss_pct}    one_way_delay_ms=${delay_ms}    jitter_ms=${jitter_ms}    seed=${seed}
    POST On Session    sat    /admin/link    json=${body}

Register Device
    [Arguments]    ${imsi}    ${expected_status}=200
    ${body}=    Create Dictionary    imsi=${imsi}
    ${resp}=    POST On Session    sat    /devices/register    json=${body}    expected_status=${expected_status}
    RETURN    ${resp}

Send Message
    [Arguments]    ${from}    ${text}=Hello from orbit    ${sos}=${False}    ${expected_status}=any
    ${body}=    Create Dictionary    from_imsi=${from}    to=+15550100    text=${text}    sos=${sos}
    ${resp}=    POST On Session    sat    /messages    json=${body}    expected_status=${expected_status}
    RETURN    ${resp}
