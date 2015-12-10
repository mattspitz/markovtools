import json
import logging
import os

START_TOK = "<START>"
END_TOK = "<END>"

def tplkey_to_jsonkey(tpl):
    return "|||".join(tpl)
def jsonkey_to_tplkey(jsonkey):
    return tuple(jsonkey.split("|||"))

def dump_model(model, output_fn):
    """ Convert our models to a JSON-friendly format.

    Specifically, the keys for n-grams must be strings, not integers.  The model_keys must also be strings, not tuples.

    We could one-line this, but it would be wrong. """
    converted = {}

    for n, token_dct in model.iteritems():
        converted[n] = dict( (tplkey_to_jsonkey(tplkey), val) for tplkey, val in token_dct.iteritems() )
    json.dump(converted, open(output_fn, "w"))

def load_model(input_fn):
    """ Convert from JSON-friendly format (above) to our expected model format.

    We could one-line this, but it would be wrong. """
    loaded = json.load(open(input_fn, "r"))

    converted = {}
    for n, token_dct in loaded.iteritems():
        converted[int(n)] = dict( (jsonkey_to_tplkey(jsonkey), val) for jsonkey, val in token_dct.iteritems() )
    return converted

def configure_logging():
    log_level = logging.ERROR
    if os.environ.get("DEBUG"):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
                        format="%(levelname)s:%(message)s")
