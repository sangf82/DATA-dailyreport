def post_process_to_sql(response_obj: dict) -> str:
    return "SELECT COUNT(*) FROM db.table where condition"