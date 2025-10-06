source(findFile('scripts', 'antares-setup.py'))


def main():
    Setup( {'IVIApp': 'launch'} )
    
    test.log("Verify each tab screen is correctly displayed")
    
    Ivi.select_tab("Vehicle")
    saveObjectSnapshot(Ivi.objects.appWindow(), "vehicle-page.xml")
    
    Ivi.select_tab("Media")
    saveObjectSnapshot(Ivi.objects.appWindow(), "media-page.xml")
        
    Ivi.select_tab("Navigation")
    saveObjectSnapshot(Ivi.objects.appWindow(), "navigation-page.xml")