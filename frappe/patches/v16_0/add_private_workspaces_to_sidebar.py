import click

import nts


def execute():
	from nts.query_builder import DocType

	workspace = DocType("Workspace")
	all_workspaces = (nts.qb.from_(workspace).select(workspace.name).where(workspace.public == 0)).run(
		pluck=True
	)
	from nts.desk.doctype.workspace_sidebar.workspace_sidebar import add_to_my_workspace

	for space in all_workspaces:
		workspace_doc = nts.get_doc("Workspace", space)
		add_to_my_workspace(workspace_doc)
	# save the sidebar items
	nts.db.commit()  # nosemgrep
