import nts
import nts.utils
from nts import _
from nts.core.doctype.user_invitation.user_invitation import UserInvitation


@nts.whitelist(methods=["POST"])
def invite_by_email(
	emails: str, roles: list[str], redirect_to_path: str, app_name: str = "nts"
) -> dict[str, list[str]]:
	UserInvitation.validate_role(app_name)

	# validate emails
	nts.utils.validate_email_address(emails, throw=True)
	email_list = nts.utils.split_emails(emails)
	if not email_list:
		nts.throw(title=_("Invalid input"), msg=_("No email addresses to invite"))

	# get relevant data from the database
	disabled_user_emails = nts.db.get_all(
		"User",
		filters={"email": ["in", email_list], "enabled": 0},
		pluck="email",
	)
	accepted_invite_emails = nts.db.get_all(
		"User Invitation",
		filters={
			"email": ["in", email_list],
			"status": "Accepted",
			"app_name": app_name,
			"user": ["is", "set"],
		},
		pluck="email",
	)
	pending_invite_emails = nts.db.get_all(
		"User Invitation",
		filters={"email": ["in", email_list], "status": "Pending", "app_name": app_name},
		pluck="email",
	)

	# create invitation documents
	to_invite = list(
		set(email_list) - set(disabled_user_emails) - set(accepted_invite_emails) - set(pending_invite_emails)
	)
	for email in to_invite:
		nts.get_doc(
			doctype="User Invitation",
			email=email,
			roles=[dict(role=role) for role in roles],
			app_name=app_name,
			redirect_to_path=redirect_to_path,
		).insert(ignore_permissions=True)

	return {
		"disabled_user_emails": disabled_user_emails,
		"accepted_invite_emails": accepted_invite_emails,
		"pending_invite_emails": pending_invite_emails,
		"invited_emails": to_invite,
	}


@nts.whitelist(allow_guest=True, methods=["GET"])
def accept_invitation(key: str) -> None:
	_accept_invitation(key, False)


# `app_name` is required for security
@nts.whitelist(methods=["PATCH", "POST"])
def cancel_invitation(name: str, app_name: str):
	UserInvitation.validate_role(app_name)

	if not nts.db.exists("User Invitation", name):
		nts.throw(title=_("Error"), msg=_("Invitation not found"))

	invitation = nts.get_doc("User Invitation", name)
	if invitation.app_name != app_name:
		# message is not specific enough for security
		nts.throw(title=_("Error"), msg=_("Invitation not found"))

	if invitation.status == "Cancelled":
		return {"cancelled_now": False}

	if invitation.status != "Pending":
		nts.throw(title=_("Error"), msg=_("Invitation cannot be cancelled"))

	invitation.flags.ignore_permissions = True
	return {"cancelled_now": invitation.cancel_invite()}


@nts.whitelist(methods=["GET"])
def get_pending_invitations(app_name: str):
	UserInvitation.validate_role(app_name)

	pending_invitations = nts.db.get_all(
		"User Invitation", fields=["name", "email"], filters={"status": "Pending", "app_name": app_name}
	)
	res = []
	for pending_invitation in pending_invitations:
		roles = nts.db.get_all("User Role", fields=["role"], filters={"parent": pending_invitation.name})
		res.append(
			{
				"name": pending_invitation.name,
				"email": pending_invitation.email,
				"roles": [r.role for r in roles],
			}
		)
	return res


def _accept_invitation(key: str, in_test: bool) -> None:
	# get invitation
	hashed_key = nts.utils.sha256_hash(key)
	invitation_name = nts.db.get_value("User Invitation", filters={"key": hashed_key})
	if not invitation_name:
		nts.throw(title=_("Error"), msg=_("Invalid key"))
	invitation = nts.get_doc("User Invitation", invitation_name)

	# accept invitation
	invitation.accept(ignore_permissions=True)

	user = nts.get_doc("User", invitation.email)
	should_update_password = not user.last_password_reset_date and not bool(
		nts.get_system_settings("disable_user_pass_login")
	)

	# set redirect_to
	redirect_to = nts.utils.get_url(invitation.get_redirect_to_path())
	if should_update_password:
		redirect_to = f"{user.reset_password()}&redirect_to=/{invitation.get_redirect_to_path()}"

	# GET requests do not cause an implicit commit
	nts.db.commit()  # nosemgrep

	if not in_test and not should_update_password:
		nts.local.login_manager.login_as(invitation.email)

	# set response
	nts.local.response["type"] = "redirect"
	nts.local.response["location"] = redirect_to
