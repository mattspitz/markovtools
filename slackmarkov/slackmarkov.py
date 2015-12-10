from __future__ import print_function

import argparse
import collections
import logging
import os.path
import random
import re
import sys
import time

import leveldb
import slacker


def get_leveldb():
    return leveldb.LevelDB(os.path.join(os.path.dirname(__file__), "db"))


def get_slack(api_key):
    return slacker.Slacker(api_key)


def _msg_key(channel_id, msg_ts):
    return "{}-msg-{}".format(channel_id, msg_ts)


def _update_channel(channel_id, slack, db):
    added = 0
    latest = time.time()
    while True:
        response = slack.channels.history(channel_id, latest=latest, inclusive="0", count=1000)
        for msg in response.body["messages"]:
            if msg["type"] == "message" and "subtype" not in msg:
                key = _msg_key(channel_id, msg["ts"])
                # TODO: This will fetch until we find a message we already
                #       have; if the database failed to fetch while initially
                #       populating, we may be missing older results
                try:
                    db.Get(key)
                    return added
                except KeyError:
                    db.Put(key, msg["text"].encode("utf8"))
                    added += 1

            # min() to fetch further back in history
            latest = min(latest, float(msg["ts"]))

        if not response.body["has_more"]:
            return added


def pull_messages(api_key, channel_ids):
    slack = get_slack(api_key)
    db = get_leveldb()

    for channel_id in channel_ids:
        num_added = _update_channel(channel_id, slack, db)
        logging.debug("%s: added %s", channel_id, num_added)


class MarkovModel(object):
    STOP_SENTINEL = "<STOP>"

    def __init__(self, order):
        self.order = order
        self.model = collections.defaultdict(collections.Counter)

    def _normalize(self, word):
        if word.startswith("@"):
            return None
        # starts with a letter, strip trailing non-letters
        regex = re.compile(r"^([a-zA-Z]+?(.*?))[^a-zA-Z]*$")
        match = regex.match(word)
        if match:
            return match.group(1).lower()
        return None

    def add_msg(self, msg):
        """Normalizes and adds a message to the model."""
        normalized = []
        for word in msg.split():
            new = self._normalize(word)
            if new:
                normalized.append(new)

        prior = [ None ]
        for word in normalized + [ self.STOP_SENTINEL ]:
            self.model[tuple(prior)][word] += 1
            prior.append(word)
            prior = prior[-self.order:]

    def get_line(self):
        line = []
        prior = [ None ]
        while True:
            word = random.choice(list(self.model[tuple(prior)].elements()))
            if word == self.STOP_SENTINEL:
                break

            line.append(word)
            prior.append(word)
            prior = prior[-self.order:]

        return " ".join(line)


def build_model(channel_ids, order):
    db = get_leveldb()
    model = MarkovModel(order)
    for channel_id in channel_ids:
        for _, msg in db.RangeIter(_msg_key(channel_id, 0), _msg_key(channel_id, 9999999999999)):
            model.add_msg(msg.decode("utf8"))
    return model


def get_channel_id(api_key, channel_name):
    slack = get_slack(api_key)
    for channel in slack.channels.list().body["channels"]:
        if channel["name"] == channel_name:
            return channel["id"]
    return None


def print_messages(channel_ids, order, num_messages):
    model = build_model(channel_ids, order)

    for _ in xrange(num_messages):
        print(model.get_line())


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    parser_get_channel = subparsers.add_parser("get_channel", help="Prints channel ID")
    parser_get_channel.add_argument("--api_key", required=True, help="API key for the Slackbot used to pull/post messages")
    parser_get_channel.add_argument("channel_names", nargs="+", help="Channel name(s) for which to fetch an ID.")

    parser_update = subparsers.add_parser("update", help="Updates channel models")
    parser_update.add_argument("--api_key", required=True, help="API key for the Slackbot used to pull/post messages")
    parser_update.add_argument("channel_ids", nargs="+", help="Channel(s) to update")

    parser_print = subparsers.add_parser("print", help="Prints message based on content of channels")
    parser_print.add_argument("--order", default=2, type=int, help="Markov model order to use")
    parser_print.add_argument("--num_messages", default=10, type=int, help="Number of messages to print")
    parser_print.add_argument("channel_ids", nargs="+", help="Channel(s) on which to base a message")

    # TODO post?

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "get_channel":
        for channel_name in args.channel_names:
            channel_id = get_channel_id(args.api_key, channel_name)
            if channel_id is None:
                print("Unrecognized channel name: '{}'".format(channel_name), file=sys.stderr)
                sys.exit(1)
            else:
                print(channel_id)

    elif args.command == "update":
        pull_messages(args.api_key, args.channel_ids)

    elif args.command == "print":
        if args.order <= 0:
            raise Exception("Order must be positive.")
        if args.num_messages <= 0:
            raise Exception("Number of messages must be positive.")
        print_messages(args.channel_ids, args.order, args.num_messages)

    else:
        raise Exception("Invalid command: {}".format(args.command))


if __name__ == "__main__":
    logging.basicConfig(level=(logging.DEBUG if os.environ.get("DEBUG") else logging.ERROR))
    main()
