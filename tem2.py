s = '''
    INSERT INTO 
    `users` 
    (`email`, `password`, `admin`, `name`, `image`, `create_at`, `id)
    VALUES 
    (?, ?, ?, ?, ?, ?, ?)
    '''

print(s)