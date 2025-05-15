from flask import render_template, flash, redirect, url_for, request
from flaskapp import app, db
from flaskapp.models import BlogPost, IpView, Day, UkData
from flaskapp.forms import PostForm
import datetime
import numpy as np
import pandas as pd
import json
import plotly
import plotly.express as px


# Route for the home page, which is where the blog posts will be shown
@app.route("/")
@app.route("/home")
def home():
    # Querying all blog posts from the database
    posts = BlogPost.query.all()
    return render_template('home.html', posts=posts)


# Route for the about page
@app.route("/about")
def about():
    return render_template('about.html', title='About page')


# Route to where users add posts (needs to accept get and post requests)
@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=1)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)


# Route to the dashboard page
@app.route('/dashboard')
def dashboard():
    days = Day.query.all()
    df = pd.DataFrame([{'Date': day.id, 'Page views': day.views} for day in days])

    fig = px.bar(df, x='Date', y='Page views')

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('dashboard.html', title='Page views per day', graphJSON=graphJSON)


@app.route("/scatter")
def scatter():
    data = UkData.query.all()
    df1 = pd.DataFrame([{'Percentage population female %': dat.c11Female, 
                         'Constituency': dat.constituency_name,
                         'Turnout 2019 elections %': dat.Turnout19,
                         'Country': dat.country} 
                         for dat in data])    
    
    fig1 = px.scatter(df1, x='Percentage population female %', y='Turnout 2019 elections %', color = 'Country', 
                      hover_data = ["Constituency"],
                      title="Voter Turnout (%) Against Female Population (%) of UK Constituencies, coloured by country, for the 2019 General Elections.")

    graph2JSON = {
    "data": fig1["data"],
    "layout": fig1["layout"]
}
    return render_template('scatter.html', title='Scatterplot', graph2JSON=json.dumps(graph2JSON, cls=plotly.utils.PlotlyJSONEncoder))


@app.route("/barplot")
def barplot():
    data = UkData.query.all()

    # Create a DataFrame
    df2 = pd.DataFrame([{
        'Constituency': dat.constituency_name,
        'Region': dat.region,
        'Female %': dat.c11Female,
        'Con': dat.ConVote19,
        'Lab': dat.LabVote19,
        'LibDem': dat.LDVote19,
        'SNP': dat.SNPVote19,
        'PC': dat.PCVote19,
        'UKIP': dat.UKIPVote19,
        'Green': dat.GreenVote19,
        'Brexit': dat.BrexitVote19,
        'Turnout 2019 %': dat.Turnout19} for dat in data])

   #Take 5 constituencies with smallest and largerst female population
    df2_nsmall = df2.nsmallest(5, 'Female %').copy()
    df2_nsmall['Group'] = 'Min'

    df2_nlarge = df2.nlargest(5, 'Female %').copy()
    df2_nlarge['Group'] = 'Maj'
    
    df3 = pd.concat([df2_nsmall, df2_nlarge])

    df_long = df3.melt(
        id_vars=['Constituency', 'Group'],
        value_vars=['Lab', 'Green', 'SNP', 'LibDem', 'Con',  'Brexit'],
        var_name='Party',
        value_name='votes')

    # Combinations Demography + Party for colours in barplot
    df_long['Female Minority/Majority & Party'] = df_long['Group'] + '-' + df_long['Party']

    # Own Colours for Barplot
    color_map = {
    'Min-Lab':     '#cce5ff',  # pale blue
    'Min-Green':   '#66a3ff',  # sky blue
    'Min-SNP':     '#0073e6',  # strong blue
    'Min-LibDem':  '#4c4cff',  # blue-violet
    'Min-Con':     '#9933ff',  # medium purple
    'Min-Brexit':  '#4b0082',  # indigo

    'Maj-Lab':     '#ffe6ec',  # pale pink
    'Maj-Green':   '#ffb3c6',  # baby pink
    'Maj-SNP':     '#ff6699',  # warm pink
    'Maj-LibDem':  '#ff3366',  # hot pink
    'Maj-Con':     '#e60026',  # crimson red
    'Maj-Brexit':  '#990000'}   # dark red
   

# Create histogram
    fig2 = px.histogram(
        df_long,
        x='Constituency',
        y='votes',
        color='Female Minority/Majority & Party',
        barmode='stack',
        color_discrete_map=color_map,
        title='Votes per Party in 2019 UK General Elections for Constituencies with Smallest and Largest Female Population (%) Respectively')
    
    graph1JSON = {"data": fig2["data"], "layout": fig2["layout"]}
    return render_template('barplot.html', title='Barplot', graph1JSON=json.dumps(graph1JSON, cls=plotly.utils.PlotlyJSONEncoder))


@app.before_request
def before_request_func():
    day_id = datetime.date.today()  # get our day_id
    client_ip = request.remote_addr  # get the ip address of where the client request came from

    query = Day.query.filter_by(id=day_id)  # try to get the row associated to the current day
    if query.count() > 0:
        # the current day is already in table, simply increment its views
        current_day = query.first()
        current_day.views += 1
    else:
        # the current day does not exist, it's the first view for the day.
        current_day = Day(id=day_id, views=1)
        db.session.add(current_day)  # insert a new day into the day table

    query = IpView.query.filter_by(ip=client_ip, date_id=day_id)
    if query.count() == 0:  # check if it's the first time a viewer from this ip address is viewing the website
        ip_view = IpView(ip=client_ip, date_id=day_id)
        db.session.add(ip_view)  # insert into the ip_view table

    db.session.commit()  # commit all the changes to the database
