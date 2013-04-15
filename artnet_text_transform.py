import re
import os
import sys
import glob
import codecs

def clean_up_text(orig):
	
	# Note: The while loops are here because some of these routines
	#   need multiple passes through the text to catch all of the instances
	
	s = orig
	
	# Get rid of body blank lines
	n = 1
	while n > 0:
		s,n = re.subn(r'\n[ \t]*\n', r'\n', s)
		# print 'body blanks', n

	# Combine result number and artist name and add Artist field name
	s,n = re.subn(r'\n(?:Full details\t\n)?([0-9]+)\t\n \t ?(.*)\n', r'\nArtist\t\g<2>\t\g<1>\n', s)
	# print 'artist field', n

	# Try first line, Combine result number and artist name and add Artist field name
	s,n = re.subn(r'^(?:Full details\t\n)?([0-9]+)\t\n \t ?(.*)\n', r'\nArtist\t\g<2>\t\g<1>\n', s)
	# print 'artist field', n

	# Concatenate continued lines (which don't contain tabs) and replace newline with space:
	n = 1
	while n > 0:
		s,n = re.subn(r'\n([^\t]*)\n', r' \g<1>\n', s)
		# print 'continued lines', n
	
	# Get rid of first blank line(s)
	n = 1
	while n > 0:
		s,n = re.subn(r'^[ \t]*\n', r'', s)
		# print 'first blank line', n
	
	# Remove final trailing newline if it exists
	if s[-1] == '\n':
		s = s[:-1]
		# print 'final newline'

	return s

# --------------------------
# Main body of the script
if len(sys.argv) < 2:
	sys.exit('\nUsage: python %s artnet_output.txt\nor\npython %s dir_of_artnet_txt_files\n' % (sys.argv[0], sys.argv[0]))

if not os.path.exists(sys.argv[1]):
	sys.exit('ERROR: Directory or file %s was not found!' % sys.argv[1])
else:
	
	# Single input .txt file
	if os.path.isfile(sys.argv[1]):
		in_name = os.path.abspath(sys.argv[1])
		f = codecs.open(in_name, 'r', 'utf-8')
		s = f.read()
		f.close()
		
		# Process text
		s = clean_up_text(s)

		# Create output file name from input, adding _out before extension
		# If file already exists, add datetime for human-readable unique name
		in_name_split = os.path.splitext(in_name)
		out_name = in_name_split[0] + '_out' + in_name_split[1]
		
		if os.path.exists(out_name):
			import datetime
			out_name = in_name_split[0] + '_' + re.sub(r'[- .:]', '_', unicode(datetime.datetime.now())) + '_out' + in_name_split[1]
	
	# Concatenate all .txt files in given directory
	elif os.path.isdir(sys.argv[1]):
		dir = os.path.abspath(sys.argv[1])
		in_files = glob.glob(os.path.join(dir, '*.txt'))
		
		s = ''
		
		for ii, file in enumerate(in_files):
			# print file, ii+1, '/', len(in_files)
			f = codecs.open(file, 'r', 'utf-8')
			s_tmp = f.read()
			f.close()
			
			# clean up individually because there are different patterns for
			# text which has been copied and pasted out of original web page
			# vs out of print window
			if ii == 0:
				s = clean_up_text(s_tmp)
			else:
				s = s + u'\n' + clean_up_text(s_tmp)

			# Create output file name from input directory name, adding _out.txt 
			# If file already exists, add datetime for human-readable unique name
			out_name = dir + '_out.txt'
		
			if os.path.exists(out_name):
				import datetime
				out_name = dir + re.sub(r'[- .:]', '_', unicode(datetime.datetime.now())) + '_out.txt'
	
	# Write output string to file (at least for now)
	f = codecs.open(out_name, 'w', 'utf-8')
	f.write(s)
	f.close()

	columns = {}
	fields = ['Artist','Title','Description','Medium','Year of Work','Printing/Casting',
					  'Size','Edition','Cat. Rais.','Found./Pub.','Misc.','Sale of','Estimate','Sold For',
					  'Provenance','Exhibition','Literature']
	for field in fields:
		columns[field] = []
	
	lines = s.split('\n')
	n_lines = len(lines)
	
	data = {}
	
	for ii in range(n_lines):
		kv = lines[ii].split('\t')
		k = kv[0]
		v = kv[1]
		
		if (k == 'Artist' and len(kv) > 3) or (k != 'Artist' and len(kv) > 2):
			sys.exit('line ' + str(ii) + ' splits into ' + str(len(kv)) + ' pieces!!')
			
		if k == 'Artist' and ii > 0:
			# hit a new data item, so record this one in columns
			for field in fields:
				if field in data:
					columns[field].append(data[field])
				else:
					columns[field].append('')
			
			# reset data for new item
			data = {}
		
		if k not in columns:
			sys.exit('Unexpected field "' + k + '" found but not in specified data columns!')
		
		data[k] = v.strip()
	
	# record last data item in columns
	for field in fields:
		if field in data:
			columns[field].append(data[field])
		else:
			columns[field].append('')

	# check whether all fields have same length
	lens = [len(v) for k,v in columns.iteritems()]
	for l in lens:
		if l != lens[0]:
			sys.exit('column lengths not all equal! ' + str(lens))
	
	n_records = lens[0]

	# Create new price USD column based on Sold for
	price_field = 'Selling price USD'
	fields.append(price_field)
	columns[price_field] = []
	re_price = re.compile( r"(^|.*[ (])([0-9,]+) USD.*" )
	for jj in range(n_records):
		p_match = re_price.match(columns['Sold For'][jj])
		if p_match:
			p_str = re.sub(r',', r'', p_match.group(2))
			columns[price_field].append(p_str)
		else:
			columns[price_field].append('')

	# Write results out to tab-separated-value text file
	base_name, ext = os.path.splitext(out_name)
	out_tsv_name = base_name + '.tsv'
	
	f = codecs.open(out_tsv_name, 'w', 'utf-8')
	f.write('\t'.join(fields) + '\n')
	
	for jj in range(n_records):
		values = [columns[key][jj] for key in fields]
		f.write('\t'.join(values) + '\n')
	
	f.close()
		
	

