#!/usr/bin/python
# CharGer - Characterization of Germline variants
# author: Adam D Scott (ascott@genome.wustl.edu) & Kuan-lin Huang (khuang@genome.wustl.edu)
# version: v0.0 - 2015*12

import sys
import getopt
from entrezAPI import entrezAPI
from exacAPI import exacAPI
from variant import variant
from variant import MAFVariant
from autovivification import autovivification

class charger(object):
	def __init__( self , **kwargs ):
		self.userVariants = kwargs.get( 'variants' , [] )
		self.userExpression = kwargs.get( 'expressions' , [] )
		self.userGeneList = kwargs.get( 'geneList' , autovivification({}) )
		self.clinvarVariants = kwargs.get( 'clinvarVariants' , autovivification({}) )

### Retrieve input data from user ###
	def getInputData( self  , **kwargs ):
		mafFile = kwargs.get( 'maf' , "" )
		expressionFile = kwargs.get( 'expression' , "" )
		geneListFile = kwargs.get( 'geneList' , "" )
		self.readMAF( mafFile )
		self.readExpression( expressionFile )
		self.readGeneList( geneListFile )
	def readMAF( inputFile ):
		print "\tSplitting .maf by variant type!"
		if inputFile:
			inFile = open( inputFile , 'r' )
			next(inFile)
			for line in inFile:
				fields = line.split( "\t" )
				var = MAFVariant()
				var.mafLine2Variant( line )
				self.userVariants.append( var )
	def readExpression( inputFile ): # expect a sample(col)-gene(row) matrix
		if inputFile:
			inFile = open( inputFile , 'r' )
			header = inFile.readline() # for future fetch header to get other field
			samples = header.split( "\t" )
			for line in inFile:
				fields = line.split( "\t" )
				gene = fields[0]
				for i in range(1,len(fields)):
					self.userExpression[samples[i]][gene] = fields[i]
	def readGeneList( inputFile, diseaseSpecific = True ): # gene list formatted "gene", "disease", "mode of inheritance"
		if inputFile:
			inFile = open( inputFile , 'r' )
			for line in inFile:
				fields = line.split( "\t" )
				gene = fields[0]
				if diseaseSpecific:
					disease = fields[1]
				else: #set the gene to match all disease
					disease = "all" 
				mode_inheritance = fields[2]
				self.userGeneList[gene][disease] = mode_inheritance

### Retrieve external reference data ###
	def getExternalData( self , **kwargs ):
		doClinVar = kwargs.get( 'clinvar' , True )
		doExAC = kwargs.get( 'exac' , True )

### Evidence levels ### 
##### Very Strong #####
	def PVS1( expressionThreshold = 0.05 ):
		truncations = ["Frame_Shift_Del","Frame_Shift_Ins","Nonsense_Mutation","Nonstop_Mutation","Splice_Site"]
		if geneList: #gene, disease, mode of inheritance
			for var in self.userVariants:
				varGene = var.gene
				varDisease = var.disease	
				varSample = var.sample
				varClass = var.variantClass
				if varClass in truncations:
					if varGene in geneList: # check if in gene list
						if ( "dominant" in self.userGeneList[varGene][varDisease] or \
							"dominant" in self.userGeneList[varGene]["all"]):
							var.PVS1 = True # if call is true then check expression effect
							if expression: # consider expression data only if the user has supplied an expression matrix
								if expression[varSample][varGene] >= expressionThreshold:
									var.PVS1 = False 
		else: 
			print "CharGer Error: Cannot evaluate PVS1: No gene list supplied."
			#raise Exception("No gene list file supplied.")
##### Strong #####
	def PS1( clinvarVariants , clinvarClinical ):
		print "CharGer module PS1"
		print "- same peptide change that is pathogenic and is a different genomic variant of the same reference peptide"
		peptideChange( clinvarVariants , clinvarClinical , "PS1" )
##### Moderate #####
	def PM2( clinvarVariants , clinvarClinical ):
		for var in self.userVariants:
			#varMAF = var.getExACasdf # Adam will update use alleleFrequency method
			if isFrequentAllele(var):
				var.PM2 = True
	def PM4( ):
		lenShift = ["In_Frame_Del","In_Frame_Ins","Nonstop_Mutation"]
		for var in self.userVariants:
			varClass = var.variantClass
			if varClass in lenShift:
				var.PM4 = True
	def PM5( clinvarVariants , clinvarClinical ):
		print "CharGer module PM5"
		print "- different peptide change of a pathogenic variant at the same reference peptide"
		peptideChange( clinvarVariants , clinvarClinical , "PM5" )

### helper functions of evidence levels ###
	def peptideChange( clinvarVariants , clinvarClinical , mod ):
		for var in self.userVariants:
			uniVar = var.uniqueVar()
			#print "\tInput variant: " + genVar , 
			canBePS1 = True
			canBePM5 = True
			pm1Call = False
			pm5Call = False
			call = var.PS1
			#print "Call: " + genVar ,
			#print " => " + str(call)
			if not call: #is already true
				#print "checking"
				call = False
				for uid in clinvarVariants:
					var = clinvarVariants[uid]
					if uid in clinvarClinical:
						clin = clinvarClinical[uid]
						if inVar.chromosome == var.chromosome and \
							inVar.start == var.start and \
							inVar.stop == var.stop and \
							inVar.reference == var.reference and \
							inVar.referencePeptide == var.referencePeptide and \
							inVar.positionPeptide == var.positionPeptide: #same genomic position & reference
							if inVar.alternatePeptide == var.alternatePeptide: #same amino acid change
								if clin["description"] == "Pathogenic":
									#print "Already called pathogenic: " ,
									#var.printVariant(' ')
									canBePS1 = False
									canBePM5 = False
								else:
									#print "This is NOT called as pathogenic: " ,
									#var.printVariant(' ')
									if mod == "PM1":
										pm1Call = True
							else: #different amino acid change ( CAN BE USED FOR PM5 )
								if clin["description"] == "Pathogenic":
									#print "Alternate peptide change called pathogenic: " ,
									#var.printVariant(' ')
									if mod == "PM5":
										pm5Call = True
								else:
									print "" , 
									#print "Alternate peptide change NOT called as pathogenic: " ,
									#var.printVariant(' ')
					else:
						print "" , 
						#print "Not given a clinical call: " ,
						#var.printVariant(' ')
				if mod == "PM1":
					if canBePS1:
						call = pm1Call
				if mod == "PM5":
					if canBePM5:
						call = pm5Call
			if mod == "PS1":
				var.PS1 = call
			if mod == "PM5":
				var.PM5 = call
	def isFrequentAllele( freq , threshold ):
		if freq > threshold:
			return True
		return False

	def prepQuery( ent ):
		var = MAFVariant()
		for var in self.userVariants:
			thisGroup = var.uniqueVar()
			ent.addQuery( var.gene , field="gene" , group=thisGroup )
			ent.addQuery( var.chromosome , field="chr" , group=thisGroup )
			ent.addQuery( var.start + ":" + var.stop , field="chrpos37" , group=thisGroup )
			ent.addQuery( "human" , field="orgn" , group=thisGroup )
			#ent.addQuery( var.variantClass , "vartype" )
			#ent.addQuery( var.referencePeptide + var.positionPeptide + var.alternatePeptide , "Variant name" )
			#var.referencePeptide , var.positionPeptide , var.alternatePeptide
		return ent

		cg = charger()
		cg.getInput( inputFile , geneListFile )
		cg.getWebData( )
		cg.PVS1( )
		cg.PS1( )
		cg.PM4( )
		cg.PM5( )

		userVariants = splitByVariantType( inputFile )
		
		calls = autovivification.autovivification({})
		if doClinVar:
			ent = entrezAPI()	
			ent = prepQuery( inputFile , ent , userVariants )
			ent.database = entrezAPI.clinvar
			clinvarEntries = ent.doBatch( 5 )
			clinvarVariants = clinvarEntries["variants"]
			clinvarTraits = clinvarEntries["traits"]
			clinvarClinical = clinvarEntries["clinical"]

			calls["PVS1"] = PVS1( userVariants , geneListFile , None , None )
			calls["PS1"] = PS1( userVariants , clinvarVariants , clinvarClinical )
			calls["PM4"] = PM4( userVariants )
			calls["PM5"] = PM5( userVariants , clinvarVariants , clinvarClinical )

		for module in calls:
			print module
			for uniVar in calls[module]:
				print uniVar ,
				if calls[module][uniVar]:
					print "\tis " + module
				else:
					print "\tis NOT " + module

		if doExAC:
			exac = exacAPI(harvard=True)
			exacEntries = exac.getAlleleFrequencies( userVariants )
			thresh = 0
			for genVar in exacEntries:
				alleleFrequency = exacEntries[genVar]
				if isFrequentAllele( alleleFrequency , thresh ):
					print genVar + " is NOT rare(" + str(thresh) + "): " + str(alleleFrequency)

	if __name__ == "__main__":
		main( sys.argv[1:] )
