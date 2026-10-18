from app import create_app
app=create_app()
if __name__=='__main__':
    from waitress import serve
    print('Cami Nails: http://127.0.0.1:5000 — mantenha esta janela aberta.')
    serve(app,host='127.0.0.1',port=5000)
