def docs_group(group_name):
    def decorator(cls):
        # This decorator does nothing, just returns the class
        return cls
    return decorator
