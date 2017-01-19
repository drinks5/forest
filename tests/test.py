from forest import Forest, text, Router

app = Forest()


router = Router()


@router('/')
def views(request):
    return text('hello world!')


print('start run:')
app.run()
