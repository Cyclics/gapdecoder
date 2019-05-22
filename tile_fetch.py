#!/usr/bin/env python3
# coding: utf-8

import base64
import hmac
import re
from pathlib import Path

from PIL import Image
import lxml.html

from lxml import etree
import requests

from decryption import decrypt

IV = bytes.fromhex("7b2b4e23de2cc5c5")


def compute_url(path, token, x, y, z):
    """
    >>> path = 'wGcDNN8L-2COcm9toX5BTp6HPxpMPPPuxrMU-ZL-W-nDHW8I_L4R5vlBJ6ITtlmONQ'
    >>> token = 'KwCgJ1QIfgprHn0a93x7Q-HhJ04'
    >>> compute_url(path, token, 0, 0, 7)
    'https://lh3.googleusercontent.com/wGcDNN8L-2COcm9toX5BTp6HPxpMPPPuxrMU-ZL-W-nDHW8I_L4R5vlBJ6ITtlmONQ=x0-y0-z7-tHeJ3xylnSyyHPGwMZimI4EV3JP8'
    """
    sign_path = b'%s=x%d-y%d-z%d-t%s' % (path.encode('utf8'), x, y, z, token.encode('utf8'))
    encoded = hmac.new(IV, sign_path, 'sha1').digest()
    signature_bytes = base64.b64encode(encoded, b'__')[:-1]
    signature = signature_bytes.decode('utf-8')
    return 'https://lh3.googleusercontent.com/%s=x%s-y%s-z%s-t%s' % (path, x, y, z, signature)


def fetch_tile(path, token, x, y, z):
    image_url = compute_url(path, token, x, y, z)
    r = requests.get(image_url)
    return decrypt(r.content)


def load_image_info(url):
    r = requests.get(url)

    image_slug, image_id = url.split('?')[0].split('/')[-2:]
    image_name = '%s - %s' % (image_slug, image_id)

    tree = lxml.html.fromstring(r.text)

    image_url = tree.xpath("//meta[@property='og:image']/@content")[0]

    meta_info_tree = etree.fromstring(requests.get(image_url + '=g').content)
    tile_info = [{k: int(v) for (k, v) in x.attrib.items()} for x in meta_info_tree.xpath('//pyramid_level')]

    path = image_url.split('/')[3]
    part = image_url.split(':', 1)[1]

    token_regex = r'"{}","([^"]+)"'.format(part)
    token = re.findall(token_regex, r.text)[0]

    tile_width = int(meta_info_tree.attrib['tile_width'])
    tile_height = int(meta_info_tree.attrib['tile_height'])

    return tile_info, (tile_width, tile_height), image_name, path, token


def load_tiles(url, z=6):
    tile_info, tile_size, image_name, path, token = load_image_info(url)
    try:
        tile = tile_info[z]
    except IndexError:
        print('Unknown zoom-level %s' % (z,))
        quit(1)

    tile = tile_info[z]
    num_tiles_x = int(tile['num_tiles_x'])
    num_tiles_y = int(tile['num_tiles_y'])
    empty_x = int(tile['empty_pels_x'])
    empty_y = int(tile['empty_pels_y'])

    width = num_tiles_x * tile_size[0] - empty_x
    height = num_tiles_y * tile_size[1] - empty_y

    img = Image.new(mode="RGB", size=(width, height))

    for x in range(num_tiles_x):
        for y in range(num_tiles_y):
            percent_complete = 100 * (y + x * num_tiles_y) // (num_tiles_y * num_tiles_x)
            print("Downloading: {}%".format(percent_complete), end='\r')
            file_path = Path() / ('%s %sx%sx%s.jpg' % (image_name, x, y, z))
            if not file_path.exists():
                tile_bytes = fetch_tile(path, token, x, y, z)
                file_path.write_bytes(tile_bytes)
            tile_img = Image.open(file_path)
            img.paste(tile_img, (x * tile_size[0], y * tile_size[1]))
    print("Downloaded all tiles")
    final_image_filename = image_name + '.jpg'
    img.save(final_image_filename)
    print("Saved the result as " + final_image_filename)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Download all image tiles from Google Arts and Culture website')
    parser.add_argument('url', type=str, help='an artsandculture.google.com url')
    parser.add_argument('--zoom', type=int, nargs='?',
                        help='Zoom level to fetch, can be negative. Will print zoom levels if omitted')

    args = parser.parse_args()

    if args.zoom is not None:
        load_tiles(args.url, args.zoom)
    else:
        tile_info, _, image_name, path, token = load_image_info(args.url)
        print('Zoom levels:')
        for i, level in enumerate(tile_info):
            print(' %i %i x %i (%i tiles)' % (
                i, level['num_tiles_x'] * 512, level['num_tiles_y'] * 512,
                (level['num_tiles_x'] * level['num_tiles_y'])))


if __name__ == '__main__':
    main()
