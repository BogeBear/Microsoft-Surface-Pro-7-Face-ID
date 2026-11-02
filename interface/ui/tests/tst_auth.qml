import QtQuick
import QtTest
import ".."

TestCase {
    name: "HAL authentication presentation"
    QtObject { id: fake; signal loginSucceeded(); signal loginFailed() }
    AuthStatus { id: status; backend: fake }
    HalEye { id: eye; phase: status.phase }
    function init() { status.phase="idle" }
    function test_red_while_pending() {
        verify(status.begin()); compare(status.phase,"verifying"); verify(eye.busy);
        compare(eye.light.toString(),"#ff4439");
    }
    function test_only_result_turns_green() {
        verify(status.begin()); wait(20); compare(status.phase,"verifying");
        fake.loginSucceeded(); compare(status.phase,"accepted"); compare(eye.light.toString(),"#68f7a5");
    }
    function test_failure_does_not_turn_green() {
        status.begin(); fake.loginFailed(); compare(status.phase,"denied"); compare(eye.light.toString(),"#ff4439");
        verify(status.begin()); compare(status.phase,"verifying");
    }
    function test_unsolicited_result_ignored() {
        fake.loginSucceeded(); compare(status.phase,"idle"); fake.loginFailed(); compare(status.phase,"idle");
    }
    function test_no_overlapping_attempts() { verify(status.begin()); verify(!status.begin()); }
    function test_no_restart_after_accept() { status.begin(); fake.loginSucceeded(); verify(!status.begin()); }
    function test_late_failure_cannot_overwrite_success() {
        status.begin(); fake.loginSucceeded(); fake.loginFailed(); compare(status.phase,"accepted");
    }
    function test_reduced_motion() { eye.reducedMotion=true; compare(eye.reducedMotion,true); eye.reducedMotion=false; }
}
