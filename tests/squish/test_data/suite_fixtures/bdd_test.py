source(findFile('scripts', 'python/bdd.py'))

def main():
    setupHooks()
    collectStepDefinitions()
    runFeatureFile('test.feature')
