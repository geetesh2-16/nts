import nts


def execute():
	desktop_icons = nts.get_all(
		"Desktop Icon",
		filters={
			"icon_type": "Link",
			"link_type": ["in", ["Workspace", "DocType"]],
		},
	)

	for icon in desktop_icons:
		icon_doc = nts.get_doc("Desktop Icon", icon.name)
		if nts.db.exists("Workspace Sidebar", icon.name):
			icon_doc.link_type = "Workspace Sidebar"
			icon_doc.link_to = icon.name
			icon_doc.save()

	nts.db.commit()
