def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        raise e
    if p < 1:
        p = 1
        return p

print(get_page_index('2'))