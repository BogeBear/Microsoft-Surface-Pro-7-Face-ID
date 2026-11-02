/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Diagnostic-only PAM boundary. It cannot authorize authentication.
 * No camera, password conversation, socket, template or identity backend.
 * No module options or environment variable can turn this into a success.
 */
#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <string.h>
#include <unistd.h>

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags,
                                 int argc, const char **argv)
{
    const void *service = NULL, *user = NULL, *rhost = NULL;
    (void)flags; (void)argv;
    if (argc != 0 || geteuid() != 0)
        return PAM_IGNORE;
    if (pam_get_item(pamh, PAM_SERVICE, &service) != PAM_SUCCESS || !service ||
        (strcmp(service, "sddm") && strcmp(service, "kde")))
        return PAM_IGNORE;
    /* Do not call pam_get_user: it could prompt and interfere with password UI. */
    if (pam_get_item(pamh, PAM_USER, &user) != PAM_SUCCESS || !user ||
        !*(const char *)user || strlen(user) > 256)
        return PAM_IGNORE;
    if (pam_get_item(pamh, PAM_RHOST, &rhost) != PAM_SUCCESS ||
        (rhost && *(const char *)rhost))
        return PAM_IGNORE;
    return PAM_IGNORE;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags,
                            int argc, const char **argv)
{
    (void)pamh; (void)flags; (void)argc; (void)argv;
    /* No credentials were created. This does not authenticate a user. */
    return PAM_SUCCESS;
}
