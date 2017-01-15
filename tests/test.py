from forest import Forest
from forest import text

app = Forest()


@app.route('/')
def views(request):
    return text('hello world!')


print('start run:')
app.run()
