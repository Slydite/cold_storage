/**
 * Single toggle for the "Email to Client" button on GRN/DN/Invoice.
 *
 * The backend feature is fully built and tested, but EMAIL_BACKEND on the
 * server still points at the console backend (no real Gmail App Password
 * configured yet). A clickable button would report success - the request
 * really does return 200 - while nothing is actually delivered to the
 * client. Hidden until real SMTP credentials are wired in; flip this back
 * to true then.
 */
export const EMAIL_TO_CLIENT_ENABLED = false
