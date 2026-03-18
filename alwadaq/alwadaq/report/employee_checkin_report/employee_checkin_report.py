import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "fieldname": "employee",
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "designation",
            "label": _("Designation"),
            "fieldtype": "Data",
            "width": 160,
        },
       
        {
            "fieldname": "check_in",
            "label": _("Check In"),
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "fieldname": "check_out",
            "label": _("Check Out"),
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "fieldname": "working_hours",
            "label": _("Working Hours"),
            "fieldtype": "Float",
            "width": 130,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        """
        SELECT
            ec.employee,
            e.employee_name,
            e.designation,
            DATE(ec.time) AS date,
            MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END)  AS check_in,
            MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END) AS check_out,
            ROUND(
                TIMESTAMPDIFF(
                    MINUTE,
                    MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END),
                    MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END)
                ) / 60.0,
                2
            ) AS working_hours
        FROM
            `tabEmployee Checkin` ec
        LEFT JOIN
            `tabEmployee` e ON e.name = ec.employee
        WHERE
            1=1 {conditions}
        GROUP BY
            ec.employee, DATE(ec.time)
        ORDER BY
            DATE(ec.time) DESC, ec.employee ASC
        """.format(
            conditions=conditions
        ),
        filters,
        as_dict=True,
    )

    return data


def get_conditions(filters):
    conditions = ""

    if filters.get("employee"):
        conditions += " AND ec.employee = %(employee)s"

    if filters.get("department"):
        conditions += " AND e.department = %(department)s"

    if filters.get("designation"):
        conditions += " AND e.designation = %(designation)s"

    if filters.get("from_date"):
        conditions += " AND DATE(ec.time) >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND DATE(ec.time) <= %(to_date)s"

    return conditions