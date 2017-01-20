from forest import Forest, text

app = Forest()


@app.route('/articles/{category}/{id:[0-9]+}')
async def views(request, category, id):
    return text('hello world!')


print('start run:')
app.run()
