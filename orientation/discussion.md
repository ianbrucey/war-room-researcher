
All right. So, um, here’s what I’m trying to figure out when I get back home. Um, we have one application that is built, uh, it’s a singleton application that is built to allow AI agents to work within a specific framework and draft legal documents, but also conduct accurate research.

**0:33**
One tool that we have to help us with the research portion, which is absolutely necessary, is, um, the GPT Researcher project which is open source and we can modify it. The order of the GPT Researcher is that first it takes a main query, feeds it to, um, an LLM that then generates sub-queries. Those sub-queries are taken by the research conductor and we use the Tavily API to go out into the internet. Tavily plus I think like Playwright or something, we go out to the internet, we scrape these certain URLs.

**1:37**
And then from there... yeah, we scrape these URLs and then from there... I think it, it turns the results, um, into embeddings. And then based on those embeddings, those embeddings are then, uh, synthesized or summarized and then synthesized into a report.

**2:07**
Now, here’s what... here’s what we can sort of do... or yeah, let's go through what we have to figure out. Number one: We have AI agents that we can essentially embed onto the machine, um, to handle certain portions. These AI agents can read documents, it can synthesize information, it can do multi-step operations. It can go out and search the web.

**2:46**
So one of the first things we need to tackle is how do we generate better sub-queries? And not only how do we generate better sub-queries, but let's say we have a research question specific to a case... How much of those sub-queries are dependent upon the information of the case? Or is it just... Like I guess here’s what I’m trying to figure out.

**3:34**
GPT Researcher is one application. War Room is another application. War Room is where all the good stuff is happening. It’s where all the, the reasoning and drafting and is happening. GPT Researcher is the API. But we can still utilize AI agents within the GPT Researcher.

**4:02**
So, my question is: Should we generate all the sub-queries on the War Room side, since it already has the agent working? Or should we pass the main query to GPT Researcher like we normally would, and somehow use an agent on the GPT Researcher side, um, plus some contextual information to generate some better sub-queries?

**4:39**
That's the first question. And this is not something that's trivial because sub... the sub-queries are pretty much the foundation of the research. You know, you get the best information based on the questions that you ask. So, that's an important part.

**5:02**
Now after that, we got the web search portion. Um... I mean we could save money potentially by utilizing, you know, Gemini CLI’s web search capability or even Augie CLI’s web search. But I don't think we need to do that, um, at this stage. Like, the scraping is pretty... is... is pretty well thought out.

**5:42**
But after that... the synthesis part is important. 'Cause I think right now we're doing... like we're taking these web search results and turning them into embeddings and basically the agent is synthesizing the information based off semantic... like matching. Which is good, but it could be better because again we have these CLI agents that can live on the machine and they can... they can read a document or a set of documents rather than, you know, utilizing a RAG API to, you know, possibly be accurate. You know what I mean?

**6:45**
So we need to consider that. And then... lastly... You know, given that we’re gonna be utilizing a real case. And we'll have access to actual case documents. And not just case documents, um, but like we've been using Mistral API to extract the text. Right? So we can get a motion, a 20 or 30 page motion, and we can literally provide that, or have that available in full text form for an agent to read.

**7:39**
So these are some of the questions we have to answer. Um... And then agai... and then also, you know what I mean? Like... Like because GPT Researcher can take into consideration, um, documents in its research portion, like... Like should we replace the embeddings and the synthesis part with just moving everything into documents? And then having an agent swarm read through the documents and then pro... you know, put together a synthesis of everything.

**8:30**
And should we use Mistral OCR? Like, should we pass in extract... Well, no, we don't need to use Mistral OCR because those... we already have extracted text documents. So we just would need to figure out some way to pass those extracted text documents to the API side.

**8:56**
Now, if... if the API and the other application is on the same server, then great. You know what I mean? Then we have less things to worry about. And I think we definitely should, um, consider that.
