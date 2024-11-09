from flask import Flask, render_template, request, flash
import pygal
from datetime import datetime
import csv
import os
import requests

app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = 'your secret key'

API_KEY = '5JUJV1WUJIBMM95'

timeSeries = {
    "1": "TIME_SERIES_INTRADAY",
    "2": "TIME_SERIES_DAILY",
    "3": "TIME_SERIES_WEEKLY",
    "4": "TIME_SERIES_MONTHLY"
}

def load_stock_symbols():
    filepath = os.path.join(os.path.dirname(__file__), 'data', 'stockSymbols.csv')
    stocks = []
    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stocks.append({"symbol": row['Symbol'], "name": row['Name'], "sector": row['Sector']})
    return stocks

@app.route('/', methods=['GET', 'POST'])
def index():
    stocks = load_stock_symbols()
    chart_svg = None

    symbol = request.form.get('symbol')
    chart_type = request.form.get('chart_type')
    time_series_function_key = request.form.get('time_series')
    time_series_function = timeSeries.get(time_series_function_key)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if request.method == 'POST':
        if not symbol or not time_series_function or not start_date or not end_date:
            flash("Please fill in all fields.")
            return render_template('index.html', stocks=stocks, chart_svg=chart_svg,
                                   symbol=symbol, chart_type=chart_type, time_series=time_series_function_key,
                                   start_date=start_date, end_date=end_date)

        stock_data = get_stock_data(symbol, time_series_function, start_date, end_date)
        if not stock_data:
            flash("Error getting stock data.")
            return render_template('index.html', stocks=stocks, chart_svg=chart_svg,
                                   symbol=symbol, chart_type=chart_type, time_series=time_series_function_key,
                                   start_date=start_date, end_date=end_date)

        chart_svg = plot_chart(chart_type, stock_data, f"{symbol} Stock Data ({start_date} to {end_date})")

    return render_template('index.html', stocks=stocks, chart_svg=chart_svg,
                           symbol=symbol, chart_type=chart_type, time_series=time_series_function_key,
                           start_date=start_date, end_date=end_date)

def get_stock_data(symbol, time_series_function, start_date, end_date):
    try:
        # Construct the API URL based on the selected time series function
        if time_series_function == "TIME_SERIES_INTRADAY":
            url = f"https://www.alphavantage.co/query?function={time_series_function}&symbol={symbol}&interval=15min&apikey={API_KEY}"
        else:
            url = f"https://www.alphavantage.co/query?function={time_series_function}&symbol={symbol}&apikey={API_KEY}"

        # Make the API request
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Handle API errors or informational responses
        if 'Error Message' in data or 'Information' in data:
            flash(f"API Error: {data.get('Error Message', 'No error message available')}")
            return None

        # Identify the correct key for the time series data in the response
        if time_series_function == "TIME_SERIES_DAILY":
            time_series_key = "Time Series (Daily)"
        elif time_series_function == "TIME_SERIES_WEEKLY":
            time_series_key = "Weekly Time Series"
        elif time_series_function == "TIME_SERIES_MONTHLY":
            time_series_key = "Monthly Time Series"
        elif time_series_function == "TIME_SERIES_INTRADAY":
            time_series_key = "Time Series (15min)"
        else:
            flash("Invalid time series selected.")
            return None

        # Fetch the time series data
        stock_data = data.get(time_series_key, {})

        # Filter data by date range
        filtered_data = {date: daily_data for date, daily_data in stock_data.items()
                         if start_date <= date <= end_date}

        return filtered_data

    except requests.exceptions.RequestException as e:
        flash(f"Error fetching stock data: {e}")
        return None


def plot_chart(chart_type, data, title):
    # Ensure chart_type is a string ("1" or "2")
    chart_type = str(chart_type)
    
    # Choose the correct chart type based on user input
    if chart_type == "1":
        chart = pygal.Bar()
    else:
        chart = pygal.Line()

    dates = []
    values = []
    
    # Collect and validate dates and values
    for date, daily_data in sorted(data.items()):
        # Format date and ensure '4. close' exists in daily_data
        try:
            formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
            closing_price = float(daily_data['4. close'])
        except (ValueError, KeyError) as e:
            print(f"Error processing data for date {date}: {e}")
            continue
        
        dates.append(formatted_date)
        values.append(closing_price)

    # Set chart attributes
    chart.title = title
    chart.x_labels = dates
    chart.add('Price', values)

    # Render chart to file
    chart_svg = 'static/chart.svg'
    chart.render_to_file(chart_svg)
    return chart_svg

app.run(host="0.0.0.0")
