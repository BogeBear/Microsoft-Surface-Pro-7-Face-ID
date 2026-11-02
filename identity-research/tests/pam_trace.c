/* SPDX-License-Identifier: GPL-3.0-or-later
 * Test fixture only. Arbitrary return values MUST NEVER be installed as PAM.
 */
#define PAM_SM_AUTH
#define PAM_SM_ACCOUNT
#include <security/pam_modules.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int trace(int argc, const char **argv)
{
    if (argc != 3 || strlen(argv[1]) > 64) return PAM_SYSTEM_ERR;
    FILE *f = fopen(argv[0], "a");
    if (!f) return PAM_SYSTEM_ERR;
    int ok = fprintf(f, "%s\n", argv[1]) > 0 && fclose(f) == 0;
    return ok ? atoi(argv[2]) : PAM_SYSTEM_ERR;
}
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *p,int f,int n,const char **v)
{ (void)p; (void)f; return trace(n,v); }
PAM_EXTERN int pam_sm_setcred(pam_handle_t *p,int f,int n,const char **v)
{ (void)p; (void)f; (void)n; (void)v; return PAM_SUCCESS; }
PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *p,int f,int n,const char **v)
{ (void)p; (void)f; return trace(n,v); }
