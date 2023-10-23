import math
import re
import hashlib
import os

class Calculator(object):
    def SegDepart(self, sentence):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stoptext.txt")
        StopWords = [line.strip() for line in open(path, \
                encoding='utf-8').readlines()]
        CleanSentence = re.sub('\W+', ' ', sentence)
        SentenceDepart = CleanSentence.split()

        output = []
        for word in SentenceDepart:
            word = word.lower()
            if word not in StopWords and word != '\n':
                output.append(word)
        return output


    def GetTF(self, corpus):
        tf = {}
        WordLen = len(corpus)
        for x in corpus:
            tf[x] = corpus.count(x) / WordLen
        
        return tf
    

    def GetIDF(self, corpus, data):
        freq = dict.fromkeys(corpus, 0)
            
        idf = {}
        total = len(data)

        for word in corpus:
            if freq[word] == 0:
                for d in data:
                    if word in d:
                        freq[word] += 1

        for word in freq:
            TempIDF = total / (freq[word] + 1)
            idf[word] = math.log10(TempIDF)
        return idf


    def GetTFIDF(self, input, corpuses):
        IDFInput = []
        for x in corpuses:
            WordCut = self.SegDepart(x)
            IDFInput.append(WordCut)

        input = self.SegDepart(input)
        tf = self.GetTF(input)
        idf = self.GetIDF(input, IDFInput)

        result = {}
        for key, value in tf.items():
            result[key] = value * idf[key]

        #import matplotlib.pyplot as plt
        #tf = {k: tf[k] for k in list(tf)[2:12]}
        #idf = {k: idf[k] for k in list(idf)[2:12]}
        #result = {k: result[k] for k in list(result)[2:12]}
        #D = result
        #plt.bar(range(len(D)), list(D.values()), align='center')
        #plt.xticks(range(len(D)), list(D.keys()))
        #plt.show()
        return result
    

    def cossim(self, input1, input2, lists=[]):
        result1 = self.GetTFIDF(input1, lists)
        result2 = self.GetTFIDF(input2, lists)

        WordSet = list(set(result1.keys()).union(set(result2.keys())))
        DotProduct = 0
        sq1 = 0
        sq2 = 0

        for word in WordSet:
            vector1 = result1[word] if word in result1 else 0
            vector2 = result2[word] if word in result2 else 0
            
            DotProduct += vector1 * vector2
            sq1 += pow(vector1, 2)
            sq2 += pow(vector2, 2)

        try:
            FinalResult = DotProduct / (math.sqrt(sq1) * math.sqrt(sq2))
        except ZeroDivisionError:
            FinalResult = 0

        return FinalResult


    def SortDict(self, input):
        return dict(sorted(input.items(), \
            key=lambda kv: kv[1], reverse=True))

    
    def simhash(self, input1, input2, lists=[]):
        result1 = self.GetTFIDF(input1, lists)
        result2 = self.GetTFIDF(input2, lists)

        tfidf1 = {k: result1[k] for k in list(self.SortDict(result1))[:64]}
        tfidf2 = {k: result2[k] for k in list(self.SortDict(result2))[:64]}

        fingerprint1 = [0] * 64
        fingerprint2 = [0] * 64

        for key, value in tfidf1.items():
            key = bin(int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16))[-64:]

            for i, x in enumerate(key):
                fingerprint1[i] += (value * -1) if (x == '0') else value

        for key, value in tfidf2.items():
            key = bin(int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16))[-64:]

            for i, x in enumerate(key):
                fingerprint2[i] += (value * -1) if (x == '0') else value

        hamming = 0
        for i in range(64):
            if fingerprint1[i] * fingerprint2[i] >= 0:
                hamming += 1

        return hamming / 64
    

    def UnweightedJacsim(self, input1, input2):
        result1 = set(self.SegDepart(input1))
        result2 = set(self.SegDepart(input2))
        return float(len(result1.intersection(result2)) / len(result1.union(result2)))
    

    def jacsim(self, input1, input2, lists=[]):
        result1 = self.GetTFIDF(input1, lists)
        result2 = self.GetTFIDF(input2, lists)

        WordSet = list(set(result1.keys()).union(set(result2.keys())))
        TopSum = 0
        BottomSum = 0

        for word in WordSet:
            vector1 = result1[word] if word in result1 else 0
            vector2 = result2[word] if word in result2 else 0
            
            TopSum += min(vector1, vector2)
            BottomSum += max(vector1, vector2)

        return TopSum / BottomSum
    
    """
        # Define the two texts
        def sbert(self, input1, input2):
        # Load a pre-trained BERT model (e.g., 'bert-base-uncased')
        model = SentenceTransformer('bert-base-uncased')

        # Encode the two texts
        embeddings1 = model.encode(input1, convert_to_tensor=True)
        embeddings2 = model.encode(input1, convert_to_tensor=True)

        #Compute cosine-similarities
        cossim = util.cos_sim(embeddings1, embeddings2).item()
        print(cossim)
        return cossim
    """