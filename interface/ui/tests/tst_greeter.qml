import QtQuick
import QtTest
import ".."

TestCase {
    id: test
    name: "HAL SDDM theme integration"
    width: 1280; height: 900
    QtObject {
        id: fake
        signal loginSucceeded()
        signal loginFailed()
        property int calls: 0
        function login(user, password, session) { calls++; }
    }
    ListModel {
        id: users; property string lastUser: "synthetic-test-user"
        ListElement { name: "synthetic-test-user"; realName: "Example User" }
        ListElement { name: "no-full-name"; realName: "  " }
    }
    ListModel {
        id: sessions; property int lastIndex: 0
        ListElement { name: "Synthetic session" }
    }
    Component { id: theme; Main { authBackend: fake; accounts: users; sessions: test.sessionsModel } }
    property var sessionsModel: sessions
    property var current: null
    function init() {
        fake.calls=0; current=theme.createObject(test); verify(current !== null);
    }
    function cleanup() { current.destroy(); current=null; }
    function test_submit_clears_secret_and_blocks_overlap() {
        const password=findChild(current,"secret"); password.text="synthetic-not-a-real-secret";
        current.submit(); compare(fake.calls,1); compare(password.text,"");
        compare(current.phase,"verifying"); verify(!password.enabled);
        current.submit(); compare(fake.calls,1);
        fake.loginFailed(); compare(current.phase,"denied"); verify(password.enabled);
    }
    function test_no_success_timer_in_theme() {
        current.submit(); wait(100); compare(current.phase,"verifying");
        fake.loginSucceeded(); compare(current.phase,"accepted");
    }
    function test_missing_user_does_not_submit() {
        findChild(current,"username").text=" "; current.submit(); compare(fake.calls,0);
    }
    function test_success_disables_further_submission() {
        current.submit(); fake.loginSucceeded(); current.submit(); compare(fake.calls,1);
    }
    function test_full_name_after_success() {
        current.submit(); fake.loginSucceeded();
        compare(findChild(current,"welcomeHeading").text,"Welcome, Example User");
    }
    function test_username_fallback_without_full_name() {
        findChild(current,"username").text="no-full-name"; current.submit(); fake.loginSucceeded();
        compare(findChild(current,"welcomeHeading").text,"Welcome, no-full-name");
    }
    function test_unknown_account_uses_submitted_username() {
        findChild(current,"username").text="other-account"; current.submit(); fake.loginSucceeded();
        compare(findChild(current,"welcomeHeading").text,"Welcome, other-account");
    }
    function test_no_welcome_before_success_or_after_failure() {
        current.submit(); compare(findChild(current,"welcomeHeading").text,"Verifying login");
        fake.loginFailed(); compare(findChild(current,"welcomeHeading").text,"Try again");
    }
    function test_greeting_stays_bound_to_submitted_account() {
        current.submit(); findChild(current,"username").text="other-account"; fake.loginSucceeded();
        compare(findChild(current,"welcomeHeading").text,"Welcome, Example User");
    }
    function test_name_is_plain_text() {
        findChild(current,"username").text="<b>literal-user</b>"; current.submit(); fake.loginSucceeded();
        const heading=findChild(current,"welcomeHeading");
        compare(heading.text,"Welcome, <b>literal-user</b>"); compare(heading.textFormat,Text.PlainText);
    }
    function test_fallback_prompts_password_without_submitting_or_accepting() {
        verify(current.presentPasswordFallback()); compare(fake.calls,0);
        compare(current.phase,"password_required");
        compare(findChild(current,"welcomeHeading").text,"Log in with a password");
        verify(findChild(current,"secret").enabled);
        compare(findChild(current,"halEye").light.toString(),"#ff4439");
        fake.loginSucceeded(); compare(current.phase,"password_required");
    }
    function test_password_fallback_requires_new_authentication() {
        verify(current.presentPasswordFallback());
        findChild(current,"secret").text="synthetic-not-a-real-secret";
        current.submit(); compare(fake.calls,1); compare(current.phase,"verifying");
        fake.loginFailed(); compare(current.phase,"denied");
        current.submit(); fake.loginSucceeded(); compare(current.phase,"accepted");
    }
    function test_fallback_does_not_cancel_outstanding_password_request() {
        current.submit(); verify(!current.presentPasswordFallback());
        compare(current.phase,"verifying"); current.submit(); compare(fake.calls,1);
    }
}
