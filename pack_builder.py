#!/usr/bin/env python3

import os
import argparse
import zipfile
import json
import shutil
import sys
import pexpect
import re
from pprint import pprint
from urllib import request, error, parse

def download_file(dest, url):
	try:
		f = request.urlopen(url)
		sys.stdout.write('{:100s}'.format(parse.unquote(os.path.basename(f.geturl()))))
		sys.stdout.flush()
	
		if os.path.isfile(dest +'/'+ parse.unquote(os.path.basename(f.geturl()))):
			sys.stdout.write("\t [skipped]\n")
		else:	
			with open(dest +'/'+ parse.unquote(os.path.basename(f.geturl())), "wb") as local_file:
				local_file.write(f.read())
			sys.stdout.write("\t [done]\n")

		
		return dest + '/' + parse.unquote(os.path.basename(f.geturl()))

	except error.URLError as e:
		print("URLError: ", e.reason, url)
	except error.HTTPError as e:
		print("HTTPError: ", e.code, url)

def make_dest_dir(dir):
	try:
		os.stat(dir)
	except:
		os.mkdir(dir)

def extract_file(target_file, dest_dir):
	if os.path.isdir(dest_dir):
		shutil.rmtree(dest_dir)

	with zipfile.ZipFile(target_file, "r") as zip_ref:
		zip_ref.extractall(dest_dir)

def read_pack_json(pack_dir):
	with open(pack_dir + '/manifest.json') as data_file:
		data = json.load(data_file)

	return data

def copy_mod_from_cache(mod_dir, cache_dir, project_id, file_id, show_info = False):
	mod_files = os.listdir(cache_dir + '/' + str(project_id) + '/' + str(file_id))
	for mod_file in mod_files:
		shutil.copyfile(cache_dir + '/' + str(project_id) + '/' + str(file_id) + '/' + mod_file, mod_dir + '/' + mod_file)
		if show_info:
			sys.stdout.write('{:100s}'.format(mod_file))
			sys.stdout.flush()
			sys.stdout.write("\t [skipped]\n")


def download_mod(mod_dir, cache_dir, project_id, file_id):
	try:
		if( not os.path.isdir(cache_dir + '/' + str(project_id))):
			make_dest_dir(cache_dir + '/' + str(project_id))
		if( not os.path.isdir(cache_dir + '/' + str(project_id) + '/' + str(file_id))):
			make_dest_dir(cache_dir + '/' + str(project_id) + '/' + str(file_id))
			f = request.urlopen('https://minecraft.curseforge.com/projects/' + str(project_id) + '/')
			project_url = f.geturl().replace('?cookieTest=1', '')
			download_file(cache_dir + '/' + str(project_id) + '/' + str(file_id), project_url + '/files/' + str(file_id) + '/download')
			copy_mod_from_cache(mod_dir, cache_dir, project_id, file_id)
		else:
			copy_mod_from_cache(mod_dir, cache_dir, project_id, file_id, True)
	except error.URLError as e:
		print("URLError: ", e.reason, url)
	except error.HTTPError as e:
		print("HTTPError: ", e.code, url)

def process_pack(pack_dir, server_dir, cache_dir):
	mod_manifest = read_pack_json(pack_dir)
	make_dest_dir(server_dir + '/ftb_server_pack/mods')

	overrides = os.listdir(pack_dir + '/overrides')
	for override in overrides: 
		#print(override)
		shutil.rmtree(server_dir + '/ftb_server_pack/' + override)
		shutil.copytree(pack_dir + '/overrides/' + override, server_dir + '/ftb_server_pack/' + override)	

	for mod in mod_manifest["files"]:
		download_mod(server_dir + '/ftb_server_pack/mods', cache_dir, mod["projectID"], mod["fileID"])

	base_server_dir = server_dir + '/ftb_server_pack'
	pack_server_dir = server_dir + '/' + mod_manifest["name"] + '-' + mod_manifest["minecraft"]["version"] + '-' + mod_manifest["version"]

	shutil.copytree(base_server_dir, pack_server_dir)

	pack_passed_test = False

	print('Starting Server Tests')
	while not pack_passed_test:
		pack_passed_test = test_server_setup(base_server_dir, pack_server_dir)
		
	print('All tests passed, making	server archive')
	pack_version = {'forgeVersion': '1614', 'mcVersion': mod_manifest["minecraft"]["version"], 'packVersion': mod_manifest["version"], 'packID': mod_manifest["name"], 'xml': 'modpacks'}
	with open(pack_server_dir + '/version.json', 'w') as version_file:
		json.dump(pack_version, version_file)

	shutil.make_archive(pack_server_dir + '_server', 'zip', pack_server_dir)
	print(pack_server_dir+'_server.zip created')

def test_server_setup(base_server_dir, pack_server_dir):
	print("\nTesting Server")
	eula = open(base_server_dir + '/eula.txt', 'w')
	eula.write('eula=true')
	eula.close()

	server_instance = pexpect.spawn('bash '+ base_server_dir +'/ServerStart.sh')
	err_condition = re.compile(r'^\s+(UE|UCE|UCHE|UCHIE)\s+(.*) \[(.*)\] \((.*)\)$')
	pass_condition = re.compile(r'Unloading dimension 1')
	server_pass = True
	while not server_instance.eof():
		line = server_instance.readline().decode('utf-8').rstrip()
		fail_match = err_condition.search(line)
		pass_match = pass_condition.search(line)
		if fail_match:
			server_pass = False
			jar_file = fail_match.group(4).rstrip()
			sys.stdout.write('{:100s}'.format(jar_file))
			sys.stdout.flush()
			os.remove(base_server_dir + '/mods/' + jar_file)
			os.remove(pack_server_dir + '/mods/'+ jar_file)
			sys.stdout.write("\t [removed]\n")
		if pass_match:
			server_instance.sendline('/stop')

	return server_pass
	

#def copy_pack_configs():
	# test

#def copy_pack_scripts():
	# test

#def validate_pack():
	# test

def main():
	modurl = None
	destination_directory = None

	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('--mod', dest='modurl')
	parser.add_argument('--dest', dest='destination_directory')
	args = parser.parse_args()

	mod_dir = args.destination_directory + '/modpack'
	server_dir = args.destination_directory + '/server'
	cache_dir = args.destination_directory + '/cache'

	make_dest_dir(args.destination_directory)
	make_dest_dir(cache_dir);

	mod_archive = download_file(args.destination_directory, args.modurl)
	extract_file(mod_archive, mod_dir)

	server_archive = download_file(args.destination_directory, 'https://dl.dropboxusercontent.com/u/9412612/ftb_server_pack.zip')
	extract_file(server_archive, server_dir)

	process_pack(mod_dir, server_dir, cache_dir)

if __name__ == '__main__':
	main()
