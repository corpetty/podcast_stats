import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Read the CSV file
df = pd.read_csv('podcast_episodes_logos-podcast-with-jarrad-hope.csv')

# Convert published_at and interval to datetime
df['published_at'] = pd.to_datetime(df['published_at'])
df['interval'] = pd.to_datetime(df['interval'])

# Calculate total downloads across all episodes for each interval
total_downloads_df = df.groupby('interval')['downloads_total'].sum().reset_index()
total_downloads_df['month'] = total_downloads_df['interval'].dt.to_period('M')
monthly_downloads = total_downloads_df.groupby('month')['downloads_total'].last().reset_index()
monthly_downloads['month'] = monthly_downloads['month'].astype(str)

# Calculate number of new episodes per month (excluding duplicates)
df['publish_month'] = df['published_at'].dt.to_period('M')
# Drop duplicates based on episode title before counting
unique_episodes_df = df.drop_duplicates(subset=['episode_title'])
episodes_per_month = unique_episodes_df.groupby('publish_month').size().reset_index()
episodes_per_month.columns = ['month', 'episode_count']
episodes_per_month['month'] = episodes_per_month['month'].astype(str)

# Merge the data to ensure consistent months
all_months = pd.merge(monthly_downloads, episodes_per_month, on='month', how='outer').fillna(0)
all_months = all_months.sort_values('month')

# Create the app layout
app.layout = html.Div([
    html.H1('Podcast Analytics Dashboard', style={'textAlign': 'center'}),
    
    # Combined monthly stats graph
    html.Div([
        html.H2('Monthly Downloads and New Episodes', style={'textAlign': 'center'}),
        dcc.Graph(id='monthly-stats-graph'),
    ], style={'margin': '20px'}),
    
    # Episode selector dropdown
    html.Div([
        html.Label('Select Episode:'),
        dcc.Dropdown(
            id='episode-dropdown',
            options=[{'label': title, 'value': title} for title in df['episode_title'].unique()],
            value=df['episode_title'].iloc[0],
            style={'width': '100%'}
        )
    ], style={'margin': '20px'}),
    
    # Episode-specific graph
    dcc.Graph(id='downloads-graph'),
    
    # Stats cards
    html.Div([
        html.Div([
            html.H4('Total Downloads'),
            html.H2(id='total-downloads')
        ], style={'textAlign': 'center', 'flex': 1, 'border': '1px solid #ddd', 'padding': '20px', 'margin': '10px'}),
        
        html.Div([
            html.H4('Latest Download Count'),
            html.H2(id='latest-downloads')
        ], style={'textAlign': 'center', 'flex': 1, 'border': '1px solid #ddd', 'padding': '20px', 'margin': '10px'})
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'margin': '20px'})
])

# Callback for updating the combined monthly stats graph
@app.callback(
    Output('monthly-stats-graph', 'figure'),
    Input('episode-dropdown', 'value')  # We don't actually use this input, but it helps refresh the graph
)
def update_monthly_stats_graph(_):
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add downloads bars
    fig.add_trace(
        go.Bar(
            name="Total Downloads",
            x=all_months['month'],
            y=all_months['downloads_total'],
            marker_color='rgb(55, 83, 109)',
            offsetgroup=0
        ),
        secondary_y=False,
    )

    # Add episode count bars
    fig.add_trace(
        go.Bar(
            name="New Episodes",
            x=all_months['month'],
            y=all_months['episode_count'],
            marker_color='rgb(26, 118, 255)',
            offsetgroup=1
        ),
        secondary_y=True,
    )

    # Update layout
    fig.update_layout(
        title='Monthly Downloads and New Episodes',
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Set y-axes titles
    fig.update_yaxes(title_text="Total Downloads", secondary_y=False)
    fig.update_yaxes(title_text="Number of New Episodes", secondary_y=True)
    fig.update_xaxes(title_text="Month")

    return fig

# Callback for updating the episode-specific graph
@app.callback(
    [Output('downloads-graph', 'figure'),
     Output('total-downloads', 'children'),
     Output('latest-downloads', 'children')],
    [Input('episode-dropdown', 'value')]
)
def update_graph(selected_episode):
    # Filter data for selected episode
    filtered_df = df[df['episode_title'] == selected_episode].copy()
    filtered_df = filtered_df.sort_values('interval')
    
    # Get publish date
    publish_date = filtered_df['published_at'].iloc[0].strftime('%B %d, %Y')
    
    # Calculate monthly download differences
    filtered_df['monthly_downloads'] = filtered_df['downloads_total'].diff().fillna(filtered_df['downloads_total'])
    
    # Calculate cumulative total downloads
    total_downloads = filtered_df['monthly_downloads'].sum()
    
    # Create the line graph
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=filtered_df['interval'],
            y=filtered_df['downloads_total'],
            mode='lines',
            name='Downloads'
        )
    )
    
    fig.update_layout(
        title=f'Downloads Over Time - {selected_episode}<br><sup>Published: {publish_date} | Total Downloads: {int(total_downloads):,}</sup>',
        xaxis_title='Date',
        yaxis_title='Downloads'
    )
    
    # Get latest monthly downloads
    latest_monthly_downloads = filtered_df['monthly_downloads'].iloc[-1]
    
    return fig, f"{int(total_downloads):,}", f"{int(latest_monthly_downloads):,}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port, debug=False)
