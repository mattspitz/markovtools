All methods require a Slack API key. You can get one by creating a Slackbot, which can later post messages to various channels! Get started here: `https://<YOUR-DOMAIN>.slack.com/services/new/slackbot`

### `get_channel`

Functionality relies on Slack's Channel IDs, which are separate from the channel names.

Fetch them with `get_channel`:
```
$ python markovbot.py get_channel --api_key <API_KEY> my-awesome-channel
C12345
```

### `update`

To fetch all messages for one or more channels, use the `update` command. The data is stored in a `db` folder next to the script.

`$ python markovbot.py update --api_key <API_KEY> C12345 C98765 C12345`

### `print`

To generate a new message based on the content of one or more channels, use the `print` command. `--order` defines the order of the Markov chain, or how many prior words are used to pick the next word. The larger the number, the more-specific the message. `--num_messages` indicates how many messages to print.

`$ python markovbot.py print C12345`
