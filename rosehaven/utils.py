def apply_validation_error(form, exc):
    message_dict = getattr(exc, 'message_dict', None)
    if message_dict:
        for field, errors in message_dict.items():
            target = field if field in form.fields else None
            for error in errors:
                form.add_error(target, error)
    else:
        messages = getattr(exc, 'messages', None) or [str(exc)]
        for message in messages:
            form.add_error(None, message)
