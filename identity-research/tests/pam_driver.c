/* SPDX-License-Identifier: GPL-3.0-or-later — isolated test application only. */
#include <security/pam_appl.h>
#include <stdio.h>
#include <stdlib.h>
static int no_conversation(int n, const struct pam_message **m,
                          struct pam_response **r, void *data)
{ (void)n; (void)m; (void)r; (void)data; return PAM_CONV_ERR; }
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    struct pam_conv c = {no_conversation, NULL};
    pam_handle_t *p = NULL;
    int start = pam_start_confdir(argv[2], "synthetic-test-account", &c, argv[1], &p);
    int auth = start == PAM_SUCCESS ? pam_authenticate(p, 0) : start;
    int account = auth == PAM_SUCCESS ? pam_acct_mgmt(p,0) : -1;
    int creds = auth == PAM_SUCCESS ? pam_setcred(p,PAM_ESTABLISH_CRED) : -1;
    if (p) pam_end(p,auth);
    printf("%d %d %d %d\n",start,auth,account,creds);
    return auth == atoi(argv[3]) ? 0 : 1;
}
