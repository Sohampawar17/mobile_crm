import json
import os
import calendar
import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import (
    cstr,
    get_date_str,
    today,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day,
    date_diff,
    flt,
    pretty_date,
    fmt_money,
)
from mobile.mobile_env.app_utils import (
    gen_response,
    generate_key,
    ess_validate,
    get_employee_by_user,
    validate_employee_data,
    get_ess_settings,
    get_global_defaults,
    exception_handel,
)

from erpnext.accounts.utils import get_fiscal_year

@frappe.whitelist()
def get_task_list(start=0, page_length=20, filters=None):
    try:
        frappe.log_error(title="filters",message=filters)
        tasks = frappe.get_list(
            "Task",
            fields=[
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
                "progress",
                "issue"
            ],
            filters = filters,
            start=start,
            page_length=page_length,
            order_by="modified desc",
        )
        for task in tasks:
            # if frappe.session.user == task.get("assigned_by") or frappe.session.user == task.get("completed_by") or (task.get("assigned_to") and frappe.session.user in task.get("assigned_to")):
            if task["exp_end_date"]:
                task["exp_end_date"] = task["exp_end_date"].strftime("%d-%m-%Y")
            get_task_comments(task)
            task["project_name"] = frappe.db.get_value(
                "Project", {"name": task.get("project")}, ["project_name"]
            )
            get_task_assigned_by(task)
            if task.get("assigned_to"):
                task["assigned_to"] = frappe.get_all(
                    "User",
                    filters=[["User", "email", "in", json.loads(task.get("assigned_to"))]],
                    fields=["full_name as user", "user_image"],
                    order_by="creation asc",
                )
            else:
                task["assigned_to"] = []
                # updated_task.append(task)

        return gen_response(200, "Task list getting Successfully", tasks)
    except Exception as e:
        return exception_handel(e)

def get_task_assigned_by(task):
    task["assigned_by"] = frappe.db.get_value(
        "User",
        {"name": task.get("assigned_by")},
        ["full_name as user", "user_image"],
        as_dict=1,
    )



def get_task_comments(task):
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_name": ["like", "%{0}%".format(task.get("name"))],
            "comment_type": "Comment",
        },
        fields=[
            "content as comment",
            "comment_by",
            "reference_name",
            "creation",
            "comment_email",
        ],
    )    
    for comment in comments:
        comment["commented"] = pretty_date(comment["creation"])
        comment["creation"] = comment["creation"].strftime("%I:%M %p")
        user_image = frappe.get_value(
            "User", comment.comment_email, "user_image", cache=True
        )
        comment["user_image"] = user_image

    task["comments"] = comments
    task["num_comments"] = len(comments)

def validate_assign_task(task_id):
    assigned_to = frappe.get_value(
        "Task",
        {"name": task_id},
        ["_assign", "status"],
        cache=True,
        as_dict=True,
    )

    if assigned_to.get("_assign") == None:
        frappe.throw("Task not assigned for any user")

    elif frappe.session.user not in assigned_to.get("_assign"):
        frappe.throw("You are not authorized to update this task")


@frappe.whitelist()
def update_task_status(task_id=None, new_status=None):
    try:
        if not task_id or not new_status:
            return gen_response(500, "task id and new status is required")
        validate_assign_task(task_id=task_id)
        task_doc = frappe.get_doc("Task", task_id)
        if task_doc.get("status") == new_status:
            return gen_response(500, "status already up-to-date")
        task_doc.status = new_status
        if task_doc.status == "Completed":
            task_doc.completed_by = frappe.session.user
            task_doc.completed_on = today()
        task_doc.save()
        return gen_response(200, "Task status updated successfully")

    except frappe.PermissionError:
        return gen_response(500, "Not permitted for update task")
    except Exception as e:
        return exception_handel(e)

@frappe.whitelist()
def update_task_progress(task_id=None,progress=None):
    try:
        if not task_id or not progress:
            return gen_response(500, "task id and progress is required")
        validate_assign_task(task_id=task_id)
        if progress:
            frappe.db.set_value("Task",task_id,"progress",progress)
        return gen_response(200, "Progress updated successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for update task")
    except Exception as e:
        return exception_handel(e)
    
    
    
@frappe.whitelist()
def create_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = kwargs
        if data.get("name"):
            if not frappe.db.exists("Task", data.get("name")):
                return gen_response(500, "Invalid Task id.")
            task_doc = frappe.get_doc("Task", data.get("name"))
            task_doc.update(data)
            task_doc.save()
            return gen_response(200, "Task has been Updated successfully")
        else:
            task_doc = frappe.get_doc(dict(doctype="Task"))
            task_doc.update(data)
            task_doc.insert()
        if data.get("assigned_to"):
            assignlist=data.get()
            assign_to.add(
                {
                    "assign_to": data.get("assigned_to"),
                    "doctype": task_doc.doctype,
                    "name": task_doc.name,
                }
            )
            return gen_response(200, "Task has been created successfully")
    except Exception as e:
        return exception_handel(e)
    
    
@frappe.whitelist()    
def get_task_by_id(task_id=None):
    try:
        if not task_id:
            return gen_response(500, "task_id is required", [])
        filters = [
            ["Task", "name", "=", task_id]
        ]
        tasks = frappe.db.get_value(
            "Task",
            filters,
            [
                "name",
                "subject",
                "project",
                "priority",
                'parent_task',
                "status",
                "description",
                "exp_end_date",
                "expected_time",
                "actual_time",
                "_assign as assigned_to",
                "owner as assigned_by",
                "completed_by",
                "completed_on",
                "progress",
                "issue"
            ],
            as_dict=1,
        )
        if not tasks:
            return None  # Return None if task is not found
            
        tasks["assigned_by"] = frappe.db.get_value(
            "User",
            {"name": tasks.get("assigned_by")},
            ["name","full_name as user", "full_name", "user_image"],
            as_dict=1,
        ) if tasks.get("assigned_by") else None
        
        tasks["completed_by"] = frappe.db.get_value(
            "User",
            {"name": tasks.get("completed_by")},
            ["name","full_name as user", "full_name", "user_image"],
            as_dict=1,
        ) if tasks.get("completed_by") else None
        
        tasks["project_name"] = frappe.db.get_value(
            "Project", {"name": tasks.get("project")}, ["project_name"]
        )

        if tasks.get("assigned_to"):
            assigned_to_users = frappe.get_all(
                "User",
                filters=[["User", "email", "in", json.loads(tasks.get("assigned_to"))]],
                fields=["name", "full_name as user", "full_name", "user_image"],
                order_by="creation asc",
            )
        else:
            assigned_to_users = []

        tasks["assigned_to"] = assigned_to_users


        comments = frappe.get_all(
            "Comment",
            filters={
                "reference_name": ["like", "%{0}%".format(tasks.get("name"))],
                "comment_type": "Comment",
            },
            fields=[
                "content as comment",
                "comment_by",
                "reference_name",
                "creation",
                "comment_email",
            ],
        )

        for comment in comments:
            comment["commented"] = pretty_date(comment["creation"])
            comment["creation"] = comment["creation"].strftime("%I:%M %p")
            comment["user_image"] = frappe.get_value(
                "User", comment.comment_email, "user_image", cache=True
            ) 

        tasks["comments"] = comments
        tasks["num_comments"] = len(comments)

        return gen_response(200, "Task Get Successfully",tasks)
    except frappe.PermissionError:
        return None  # Return None if permission error occurs
    except Exception as e:
        return None  # Return None for other exceptions
