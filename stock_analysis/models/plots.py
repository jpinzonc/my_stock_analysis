from bokeh.plotting import figure, output_file, show, output_notebook
from bokeh.layouts import column, row
from bokeh.models import HoverTool, ColumnDataSource

from math import pi

def stockplot(ticker, datf, field, plttype='d', pltwidth=800, pltheigth=300 ):
    inc = datf.Close > datf.Open
    dec = datf.Open > datf.Close
    if plttype == 'd':
        w = 100000
        title = " Last day ({}) behavior for {} stocks.".format(datf.Date.max().strftime('%Y%m%d'), ticker)
    elif plttype == 'pd':
        w = 60*60*10000 
        title = " Daily behavior comparison between {0} and {1} for {2} stocks".format(datf.Date.min().strftime('%Y%m%d'), datf.Date.max().strftime('%Y%m%d'), ticker)
    elif plttype == 'w':
        w = 60*60*10000 
        title = " Daily behavior comparison between {0} and {1} for {2} stocks".format(datf.Date.min().strftime('%Y%m%d'), datf.Date.max().strftime('%Y%m%d'), ticker)
    elif plttype == 'y':
        w = 60*60*60*10000 
        title = " Monthly behavior between {0} and {1} for {2} stocks".format(datf.Date.min().strftime('%Y%m%d'), datf.Date.max().strftime('%Y%m%d'), ticker)
    else:
        w = 1000
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    p = figure(x_axis_type="datetime", tools=TOOLS, width=pltwidth, height=pltheigth, title = title)
    p.xaxis.major_label_orientation = pi/4
    p.grid.grid_line_alpha=0.3
    p.segment(field, 'High', field, 'Low', source = datf,  color="black")
    source_inc = ColumnDataSource(data=datf[inc])
    source_dec = ColumnDataSource(data=datf[dec])
    p.vbar(x=field,  top='Open', bottom='Close', 
            source=source_inc, fill_color="#D5E1DD", line_color="green", width=w)
    p.vbar(x=field, top='Open', bottom='Close', 
            source=source_dec, fill_color="#D5E1DD", line_color="red", width=w)
    hover = HoverTool(tooltips=[
                                ("Open", "@Open"),
                                ("Close", "@Close"),
                                ("High", "@High"),
                                ])
    p.add_tools(hover) 
    return p 



