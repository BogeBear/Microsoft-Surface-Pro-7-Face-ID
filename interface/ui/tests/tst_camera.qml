// SPDX-License-Identifier: MIT
import QtQuick
import QtTest
import ".."

TestCase {
    id: test
    name: "Inactive camera research presentation"
    width: 1280; height: 900
    readonly property string token: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    readonly property string other: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    QtObject {
        id: fake
        signal loginSucceeded()
        signal loginFailed()
        property int calls: 0
        function login(user,password,session) { calls++; }
    }
    ListModel {
        id: users; property string lastUser: "synthetic-test-user"
        ListElement { name: "synthetic-test-user"; realName: "Example User" }
    }
    ListModel {
        id: sessions; property int lastIndex: 0
        ListElement { name: "Synthetic session" }
    }
    Component { id: theme; Main { authBackend: fake; accounts: users; sessions: test.sessionsModel } }
    Component { id: statusComponent; CameraResearchStatus {} }
    property var sessionsModel: sessions
    property var current: null
    property var status: null
    function good() { return {authentication_allowed:false,password_fallback:true,shutdown_confirmed:true,hold_required:false,evidence_eligible_for_future_validation:true}; }
    function init() { fake.calls=0; current=theme.createObject(test); status=statusComponent.createObject(test); }
    function cleanup() { current.destroy(); status.destroy(); }
    function test_never_green_from_research_completion() {
        verify(current.beginCameraResearch(token,"synthetic-test-user"));
        verify(current.finishCameraResearch(token,"synthetic-test-user",good()));
        compare(current.phase,"password_required"); compare(fake.calls,0);
        compare(findChild(current,"halEye").light.toString(),"#ff4439");
        fake.loginSucceeded(); compare(current.phase,"password_required");
    }
    function test_password_request_after_research_is_separate_authority() {
        current.beginCameraResearch(token,"synthetic-test-user");
        current.finishCameraResearch(token,"synthetic-test-user",good());
        current.submit(); compare(fake.calls,1); compare(current.phase,"verifying");
        fake.loginSucceeded(); compare(current.phase,"accepted");
        compare(findChild(current,"welcomeHeading").text,"Welcome, Example User");
    }
    function test_pending_research_blocks_password_overlap() {
        current.beginCameraResearch(token,"synthetic-test-user");current.submit();compare(fake.calls,0);
        compare(current.phase,"verifying");
        verify(!findChild(current,"secret").enabled);verify(!findChild(current,"username").enabled);
    }
    function test_pending_password_blocks_research_overlap() {
        current.submit();verify(!current.beginCameraResearch(token,"synthetic-test-user"));compare(fake.calls,1);
    }
    function test_other_account_cannot_begin_or_complete() {
        verify(!current.beginCameraResearch(token,"other"));
        verify(current.beginCameraResearch(token,"synthetic-test-user"));
        verify(!current.finishCameraResearch(token,"other",good()));compare(current.cameraResearchPhase,"capturing");
    }
    function test_wrong_or_late_attempt_ignored() {
        verify(status.begin(token,"user"));verify(!status.finish(other,"user",good()));
        verify(status.finish(token,"user",good()));verify(!status.finish(token,"user",good()));
        verify(!status.begin(token,"user"));verify(status.begin(other,"user"));
        verify(!status.finish(token,"user",good()));compare(status.phase,"capturing");
    }
    function test_timeout_requires_password_and_retains_hold() {
        verify(status.begin(token,"user"));verify(status.expire());
        compare(status.phase,"cleanup_unconfirmed");verify(status.holdRequired);verify(status.passwordRequired);
        verify(!status.finish(token,"user",good()));verify(!status.begin(other,"user"));
    }
    function test_releasing_never_means_finished() {
        verify(status.begin(token,"user"));verify(status.releasing(token,"user"));
        compare(status.phase,"releasing");verify(status.pending);verify(!status.passwordRequired);
    }
    function test_incomplete_or_forged_success_does_not_grant_login() {
        const forged=good();forged.authentication_allowed=true;
        current.beginCameraResearch(token,"synthetic-test-user");
        verify(current.finishCameraResearch(token,"synthetic-test-user",forged));
        compare(current.phase,"password_required");compare(current.cameraResearchPhase,"cleanup_unconfirmed");
        verify(!current.beginCameraResearch(other,"synthetic-test-user"));
        current.submit();compare(fake.calls,1);
    }
    function test_unknown_boolean_not_truthy_success() {
        const invalid=good();invalid.shutdown_confirmed=1;
        status.begin(token,"user");status.finish(token,"user",invalid);
        verify(status.holdRequired);compare(status.phase,"cleanup_unconfirmed");
    }
    function test_token_and_login_shape() {
        verify(!status.begin("short","user"));verify(!status.begin(token,""));verify(!status.begin(token,42));
        verify(status.begin(token,"user"));verify(!status.begin(other,"user"));
    }
    function test_backend_success_cannot_change_idle_ui() {
        fake.loginSucceeded();compare(current.phase,"idle");compare(fake.calls,0);
    }
    function test_main_timeout_switches_to_password_without_acceptance() {
        current.beginCameraResearch(token,"synthetic-test-user");
        verify(findChild(current,"cameraResearchStatus").expire());
        compare(current.phase,"password_required");compare(current.cameraResearchPhase,"cleanup_unconfirmed");
        verify(findChild(current,"secret").enabled);compare(fake.calls,0);
        fake.loginSucceeded();compare(current.phase,"password_required");
    }
    function test_actual_presentation_timer_expires() {
        verify(status.begin(token,"user"));
        tryCompare(status,"phase","cleanup_unconfirmed",8500);
        verify(status.holdRequired);verify(!status.begin(other,"user"));
    }
}
