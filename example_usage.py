from nd300 import Connection


with Connection() as connection:
    def payout():
        quantity = input('How many bills do you want to payout?')
        command, response = connection.payout(int(quantity))
        print(command)
        print(response)

    def quit():
        raise StopIteration

    def status():
        command, response = connection.status()
        print(command)
        print(response)

    def reset_dispenser():
        print(connection.reset_dispenser())

    def print_usage():
        print('p: payout bills')
        print('r: reset dispenser')
        print('s: machine status')
        print('q: quit')

    while True:
        print_usage()
        try:
            {
                'p': payout,
                'q': quit,
                's': status,
                'r': reset_dispenser,
            }[input()]()
        except KeyError:
            pass
        except StopIteration:
            break
