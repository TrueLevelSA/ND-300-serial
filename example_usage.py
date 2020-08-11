from nd300 import Connection, Command


with Connection() as connection:
    def payout():
        quantity = input('How many bills do you want to payout?')
        print(connection.send_command(Command.SINGLE_MACHINE_PAYOUT, int(quantity)))
        print('Dispensing...')
        response = connection.read_response()
        print(response)

        connection.send_command(Command.REQUEST_MACHINE_STATUS)
        response = connection.read_response()
        while response.command == Command.DISPENSING_BUSY:
            connection.send_command(Command.REQUEST_MACHINE_STATUS)
            response = connection.read_response()

        print(response)

    def quit():
        raise StopIteration

    def status():
        print(connection.send_command(Command.REQUEST_MACHINE_STATUS))
        print(connection.read_response())

    def reset_dispenser():
        print(connection.send_command(Command.RESET_DISPENSER))

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
