# Copyright (c) 2025, nts Technologies and contributors
# For license information, please see license.txt

import nts
import nts.utils
from nts import _
from nts.model.document import Document
from nts.permissions import get_roles


class UserInvitation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.core.doctype.user_role.user_role import UserRole
		from nts.types import DF

		accepted_at: DF.Datetime | None
		app_name: DF.Literal[None]
		email: DF.Data
		email_sent_at: DF.Datetime | None
		invited_by: DF.Link | None
		key: DF.Data | None
		redirect_to_path: DF.Data
		roles: DF.TableMultiSelect[UserRole]
		status: DF.Literal["Pending", "Accepted", "Expired", "Cancelled"]
		user: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		self._validate_invite()
		self.invited_by = nts.session.user
		self.status = "Pending"

	def after_insert(self):
		self._after_insert()

	def accept(self, ignore_permissions: bool = False):
		accepted_now = self._accept()
		if not accepted_now:
			return
		user, user_inserted = self._upsert_user(ignore_permissions)
		self.save(ignore_permissions)
		user.save(ignore_permissions)
		self._run_after_accept_hooks(user, user_inserted)

	@nts.whitelist()
	def cancel_invite(self):
		if self.status != "Pending":
			return False
		self.status = "Cancelled"
		self.save()
		email_title = self._get_email_title()
		nts.sendmail(
			recipients=self.email,
			subject=_("Invitation to join {0} cancelled").format(email_title),
			template="user_invitation_cancelled",
			args={"title": email_title},
			now=True,
		)
		return True

	@nts.whitelist()
	def expire(self):
		if self.status != "Pending":
			return
		self.status = "Expired"
		self.save()
		email_title = self._get_email_title()
		invited_by_user = nts.get_doc("User", self.invited_by)
		nts.sendmail(
			recipients=invited_by_user.email,
			subject=_("Invitation to join {0} expired").format(email_title),
			template="user_invitation_expired",
			args={"title": email_title},
			now=False,
		)

	def _validate_invite(self):
		self._validate_app_name()
		self._validate_roles()
		self._validate_email()
		if nts.db.get_value(
			"User Invitation",
			filters={
				"email": self.email,
				"status": "Accepted",
				"app_name": self.app_name,
				"user": ["is", "set"],
			},
		):
			nts.throw(title=_("Error"), msg=_("Invitation already accepted"))
		if nts.db.get_value(
			"User Invitation", filters={"email": self.email, "status": "Pending", "app_name": self.app_name}
		):
			nts.throw(title=_("Error"), msg=_("Invitation already exists"))
		user_enabled = nts.db.get_value("User", self.email, "enabled")
		if user_enabled is not None and user_enabled == 0:
			nts.throw(title=_("Error"), msg=_("User is disabled"))

	def _after_insert(self):
		key = nts.generate_hash()
		self.db_set("key", nts.utils.sha256_hash(key))
		invite_link = nts.utils.get_url(
			f"/api/method/nts.core.api.user_invitation.accept_invitation?key={key}"
		)
		email_title = self._get_email_title()
		nts.sendmail(
			recipients=self.email,
			subject=_("You've been invited to join {0}").format(email_title),
			template="user_invitation",
			args={"title": email_title, "invite_link": invite_link},
			now=True,
		)
		self.db_set("email_sent_at", nts.utils.now())
		return key

	def _accept(self):
		if self.status == "Accepted":
			return False
		if self.status == "Expired":
			nts.throw(title=_("Error"), msg=_("Invitation is expired"))
		if self.status == "Cancelled":
			nts.throw(title=_("Error"), msg=_("Invitation is cancelled"))
		self.status = "Accepted"
		self.accepted_at = nts.utils.now()
		self.user = self.email
		return True

	def _upsert_user(self, ignore_permissions: bool = False):
		user: Document | None = None
		user_inserted = False
		if nts.db.exists("User", self.user):
			user = nts.get_doc("User", self.user)
		else:
			user = nts.new_doc("User")
			user.user_type = "System User"
			user.email = self.email
			user.first_name = self.email.split("@")[0].title()
			user.send_welcome_email = False
			user.insert(ignore_permissions)
			user_inserted = True
		user.append_roles(*[r.role for r in self.roles])
		return user, user_inserted

	def _run_after_accept_hooks(self, user: Document, user_inserted: bool):
		user_invitation_hook = nts.get_hooks("user_invitation", app_name=self.app_name)
		if not isinstance(user_invitation_hook, dict):
			return
		for dot_path in user_invitation_hook.get("after_accept") or []:
			nts.call(dot_path, invitation=self, user=user, user_inserted=user_inserted)

	def _get_email_title(self):
		return nts.get_hooks("app_title", app_name=self.app_name)[0]

	def _validate_app_name(self):
		UserInvitation.validate_app_name(self.app_name)

	def _get_allowed_roles(self):
		user_invitation_hook = nts.get_hooks("user_invitation", app_name=self.app_name)
		if not isinstance(user_invitation_hook, dict):
			return []
		res = set[str]()
		allowed_roles_mp = user_invitation_hook.get("allowed_roles") or dict()
		only_for = set(allowed_roles_mp.keys())
		for role in only_for & set(nts.get_roles()):
			res.update(allowed_roles_mp[role])
		return list(res)

	def _validate_roles(self):
		if self.app_name == "nts":
			return
		allowed_roles = self._get_allowed_roles()
		for r in self.roles:
			if r.role in allowed_roles:
				continue
			nts.throw(
				title=_("Invalid role"),
				msg=_("{0} is not an allowed role for {1}").format(r.role, self.app_name),
			)

	def _validate_email(self):
		nts.utils.validate_email_address(self.email, throw=True)

	def get_redirect_to_path(self):
		start_index = 1 if self.redirect_to_path.startswith("/") else 0
		return self.redirect_to_path[start_index:]

	@staticmethod
	def validate_app_name(app_name: str):
		if app_name not in nts.get_installed_apps():
			nts.throw(title=_("Invalid app"), msg=_("Application is not installed"))

	@staticmethod
	def validate_role(app_name: str) -> None:
		UserInvitation.validate_app_name(app_name)
		user_invitation_hook = nts.get_hooks("user_invitation", app_name=app_name)
		only_for: list[str] = []
		if isinstance(user_invitation_hook, dict):
			only_for = list((user_invitation_hook.get("allowed_roles") or dict()).keys())
		nts.only_for(only_for)


def mark_expired_invitations() -> None:
	days = 3
	invitations_to_expire = nts.db.get_all(
		"User Invitation",
		filters={"status": "Pending", "creation": ["<", nts.utils.add_days(nts.utils.now(), -days)]},
	)
	for invitation in invitations_to_expire:
		invitation = nts.get_doc("User Invitation", invitation.name)
		invitation.expire()
		# to avoid losing work in case the job times out without finishing
		nts.db.commit()  # nosemgrep


def get_allowed_apps(user: Document | None) -> list[str]:
	user_roles = set(get_user_roles(user))
	allowed_apps: list[str] = []
	for app in nts.get_installed_apps():
		user_invitation_hooks = nts.get_hooks("user_invitation", app_name=app)
		if not isinstance(user_invitation_hooks, dict):
			continue
		only_for = list((user_invitation_hooks.get("allowed_roles") or dict()).keys())
		if set(only_for) & user_roles:
			allowed_apps.append(app)
	return allowed_apps


def get_permission_query_conditions(user: Document | None) -> str | None:
	user = get_user(user)
	user_roles = get_user_roles(user)
	if "System Manager" in user_roles:
		return
	allowed_apps = get_allowed_apps(user)
	if not allowed_apps:
		return "false"
	allowed_apps_str = ", ".join([f'"{app}"' for app in allowed_apps])
	return f"`tabUser Invitation`.app_name IN ({allowed_apps_str})"


def has_permission(
	doc: UserInvitation, user: Document | None = None, permission_type: str | None = None
) -> bool:
	return permission_type != "delete" and doc.app_name in get_allowed_apps(user)


def get_user_roles(user: Document | None) -> list[str]:
	return get_roles(get_user(user))


def get_user(user: Document | None) -> Document:
	return user or nts.session.user
