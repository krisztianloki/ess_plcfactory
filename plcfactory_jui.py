from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory UI based on Jupyterhub's ipywidgets module """

from ipywidgets import Checkbox, Text, Textarea, Button, ToggleButton, HBox, VBox, Output, Layout, HTML

widgets       = dict()
plcf_ui       = None
plcf_result   = None

plcf_output   = None

plcf_output_height = "200px"

show_plcf_out = None
plcf_out_shown = False

def hide_widget(w):
    w.layout.visibility = "hidden"


def show_widget(w):
    w.layout.visibility = "visible"


def show_wait_animation():
    global plc_result

    for c in plcf_ui.children:
        if c != plcf_result:
            c.close()
#    plcf_result.value             = "<center><b>Please wait...</b></center>"
    plcf_result.value = """
    <center><div class="loader"/></center>
    <style>
    .loader {
    border: 6px solid #f3f3f3; /* Light grey */
    border-top: 6px solid #3498db; /* Blue */
    border-radius: 50%;
    width: 45px;
    height: 45px;
    animation: spin 2s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
    </style>
    """
#    plcf_result.layout.height     = "50px"
#    plcf_result.layout.max_height = "50px"


def run_plcfactory(w):
    global plcf_output
    global plcf_result

    argv = []
    for (k,v) in widgets.iteritems():
        if isinstance(v.value, bool) and v.value:
            argv.append(k)
        elif v.value:
            if isinstance(v, Textarea):
                argv.append(k)
                for l in v.value.splitlines():
                    argv.extend(map(lambda x: str(x), l.split()))
            else:
                argv.extend([k, str(v.value)])

    show_wait_animation()

    plcf_output = Output()
    hide_widget(plcf_output)

    zipfile = None
    with plcf_output:
        from plcfactory import main as plcf
        from plcfactory import create_zipfile

        try:
            if False:
                from time import sleep
                print("Waiting 5 seconds...")
                sleep(5)
            else:
                plcf(argv)
                zipfile = create_zipfile(widgets['--device'].value)
                if zipfile:
                    link = '<center><a href="../tree/ics_plc_factory/{filename}" target="_blank" media_type="application/zip" download style="appearance:button;-webkit-appearance:square-button;-moz-appearance:button;text-decoration:none;font-weight:bold;width=100%;"><br/>&nbsp;Download!&nbsp;<br/><br/></a></center>'
                    plcf_result.value = link.format(filename = zipfile)
                else:
                    plcf_result.close()
                    show_plcfactory_output({"new":True})
        except:
            plcf_result.close()
            show_plcfactory_output({"new":True})
            raise


def show_plcfactory_output(change):
    global plcf_out_shown

    if plcf_output is None:
        return
    if change["new"]:
        if not plcf_out_shown:
            display(plcf_output)
            plcf_out_shown = True
        plcf_output.layout.height = plcf_output_height
        show_widget(plcf_output)
    else:
        hide_widget(plcf_output)
        plcf_output.layout.height = "0px"


def create_ui():
    global plcf_ui
    global plcf_result

    style = {"description_width": "initial"}

    full_width_layout = Layout(width="99%")
    templates_layout  = Layout(width="99%", height="100px")
    plc       = Checkbox(value = True, description = "Generate EEE EPICS-PLC interface", style = style, layout = full_width_layout)
    device    = Text(placholder = "device name", description = "PLC device:", style = style, layout = full_width_layout)
    eee       = Checkbox(value = True, description = "Generate EEE module", style = style, layout = full_width_layout)
    templates = Textarea(placeholder = "templates", description = "Templates to use:", style = style, layout = templates_layout)

    done      = Button(description = "Generate!", button_style = 'success', tooltip="Run PLCFactory to generate the output", layout = full_width_layout)

    widgets['--device']   = device
    widgets['--plc']      = plc
    widgets['--eee']      = eee
    widgets['--template'] = templates

    show_plcf_out = ToggleButton(description = "Show PLCFactory output", button_style = "info", style = style, layout = full_width_layout)
    show_plcf_out.observe(show_plcfactory_output, names = "value")

    done.on_click(run_plcfactory)

    plcf_result = HTML()

    plcf_ui   = VBox([device, plc, eee, templates, done, plcf_result])
    hide_widget(plcf_ui)
    plcf_ui.layout.align_items = "stretch"

    ui = VBox([show_plcf_out, plcf_ui])
    ui.layout.align_items = "stretch"
    display(ui)


def show_ui():
    show_widget(plcf_ui)


def show():
    create_ui()
    show_ui()

