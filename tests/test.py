from forest import Forest, text

app = Forest()


@app.route('/')
def views(request):
    return text('hello world!')


print('start run:')
app.run()
