import frappe
from frappe import _
from datetime import timedelta


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
            "fieldname": "shift",
            "label": _("Shift"),
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "fieldname": "shift_in_time",
            "label": _("Shift Start"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "shift_out_time",
            "label": _("Shift End"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "check_in_time",
            "label": _("Check In"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "check_out_time",
            "label": _("Check Out"),
            "fieldtype": "Time",
            "width": 110,
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

    # Fetch raw datetimes for IN/OUT — TIMESTAMPDIFF works correctly on them.
    # TIME() is NOT used in SQL because MariaDB returns timedelta objects in
    # Python, which breaks TIMESTAMPDIFF and produces NULL working_hours.
    # We strip the date component in Python post-processing instead.
    query = """
        SELECT
            ec.employee,
            e.employee_name,
            e.designation,
            DATE(ec.time)                                                   AS date,
            MAX(ec.shift)                                                   AS shift,
            MAX(st.start_time)                                              AS shift_in_time,
            MAX(st.end_time)                                                AS shift_out_time,
            MIN(CASE WHEN ec.log_type = 'IN'  THEN ec.time END)            AS check_in_dt,
            MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END)            AS check_out_dt,
            ROUND(
                TIMESTAMPDIFF(
                    MINUTE,
                    MIN(CASE WHEN ec.log_type = 'IN'  THEN ec.time END),
                    MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END)
                ) / 60.0,
                2
            )                                                               AS working_hours
        FROM
            `tabEmployee Checkin` ec
        LEFT JOIN
            `tabEmployee`   e  ON e.name  = ec.employee
        LEFT JOIN
            `tabShift Type` st ON st.name = ec.shift
        WHERE
            1=1 {conditions}
        GROUP BY
            ec.employee, DATE(ec.time)
        ORDER BY
            DATE(ec.time) DESC, ec.employee ASC
    """.format(conditions=conditions)

    rows = frappe.db.sql(query, filters, as_dict=True)

    for row in rows:
        # Convert full datetime → time-only string "HH:MM:SS" for display.
        # shift_in_time / shift_out_time come back as timedelta from MariaDB
        # TIME columns — convert those too.
        row["check_in_time"]  = _dt_to_time_str(row.get("check_in_dt"))
        row["check_out_time"] = _dt_to_time_str(row.get("check_out_dt"))
        row["shift_in_time"]  = _td_to_time_str(row.get("shift_in_time"))
        row["shift_out_time"] = _td_to_time_str(row.get("shift_out_time"))

        # Remove raw datetime keys so they don't appear as extra columns
        row.pop("check_in_dt",  None)
        row.pop("check_out_dt", None)

    return rows


# ── helpers ──────────────────────────────────────────────────────────────────

def _dt_to_time_str(dt):
    """datetime  →  'HH:MM:SS'  (or None if missing)"""
    if not dt:
        return None
    try:
        return dt.strftime("%H:%M:%S")
    except AttributeError:
        return str(dt)


def _td_to_time_str(td):
    """timedelta  →  'HH:MM:SS'  (MariaDB returns TIME columns as timedelta)"""
    if td is None:
        return None
    if isinstance(td, timedelta):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return str(td)


def get_conditions(filters):
    conditions = ""

    if not filters:
        return conditions

    if filters.get("employee"):
        conditions += " AND ec.employee = %(employee)s"

    if filters.get("department"):
        conditions += " AND e.department = %(department)s"

    if filters.get("designation"):
        conditions += " AND e.designation = %(designation)s"

    if filters.get("shift"):
        conditions += " AND ec.shift = %(shift)s"

    if filters.get("from_date"):
        conditions += " AND DATE(ec.time) >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND DATE(ec.time) <= %(to_date)s"

    return conditions