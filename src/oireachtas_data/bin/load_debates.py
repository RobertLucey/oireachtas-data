from oireachtas_data.utils import get_debates


def main():
    debates = get_debates()

    print('Loaded %s debates' % len(debates))
    print('Do something with the data in the variable \'debates\'...')

    import pdb; pdb.set_trace()

    pass


if __name__ == '__main__':
    main()
