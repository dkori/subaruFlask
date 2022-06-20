from modules.api_functions import get_dealerships, get_all_inventory
from flask import Flask, render_template, request
import pandas as pd
import requests

app = Flask(__name__)
@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/data/', methods = ['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is accessed directly. Try going to '/form' to submit form"
    if request.method == 'POST':
        # read in form data
        form_data = request.form
        # pull list of nearby dealerships
        dealership_frame = get_dealerships(form_data['zip_code'], form_data['max_distance'])
        # pull the inventory
        inventory_frame = get_all_inventory(dealership_frame, form_data)
        return render_template('simple.html',
                               tables=[inventory_frame.to_html(classes='data')],
                               titles=inventory_frame.columns.values)

app.run(host='localhost', port=5007)
