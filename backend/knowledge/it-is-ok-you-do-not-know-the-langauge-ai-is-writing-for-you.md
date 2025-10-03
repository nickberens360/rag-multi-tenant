---
title: "It's OK That You Don't Know the Language AI Is Helping You With, Kinda"
description: "An honest take on using AI to build in unfamiliar programming 
languages - the benefits, risks, and finding the right balance between capability and responsibility."
pubDate: 2025-08-14
tags: ["ai", "programming", "development", "learning", "productivity"]
author: "Probably AI"
backgroundColor: "#e0ecff"
theme: "light"
aiPrompt: "Write an article about the implications of using AI to build software in languages you don't know well. Discuss the benefits, risks, and how to balance AI assistance with understanding the underlying technology."
---

Last week I built a chatbot for my portfolio site using Python and FastAPI with a RAG architecture. I'd barely touched Python web frameworks before this. What started as a simple experiment turned into days of iterative development as I kept refining the implementation, but I had a basic working bot answering questions about my projects within the first few hours.

Was it perfect? Hell no. Did it work? Absolutely.

This experience got me thinking about something we don't talk about enough in tech circles. We're living through this weird transition where you can genuinely build stuff in languages you don't really know, thanks to AI. And I'm not sure I've figured out how to feel about it yet.

## What I'm Actually Experiencing

I've been programming for about 15 years now, and the last two have been unlike anything I've experienced before. I spun up a Flask app last month without really understanding Python decorators.

The tools are just that good now. Claude writes me functioning Rust programs. GitHub Copilot auto-completes entire functions in languages I've never touched. ChatGPT debugs my Swift code and explains exactly what went wrong.

It's like having a really smart friend who speaks every programming language fluently, sitting right next to me.

## Why I Think This Is Actually Fine (Most of the Time)

Look, purists are going to hate this take, but sometimes you just need to get stuff done.

I needed a quick script to parse some CSV files last month. Could I have spent two days learning the ins and outs of pandas? Sure. Instead, I described what I wanted to an AI, got working Python code in five minutes, and moved on with my life. The script still runs perfectly.

When I'm prototyping or exploring ideas, perfect knowledge isn't the goal. Getting from concept to working demo is. AI removes the friction of "I don't know this language well enough" that used to kill so many of my side projects before they started.

Plus, there's something to be said for learning by osmosis. After a few weeks of AI-assisted Python scripting, I actually started understanding list comprehensions and context managers. Not because I studied them, but because I kept seeing them in action.

## Where This Gets Dicey

But here's where I have to pump the brakes on my own enthusiasm.

Three months ago, I deployed a Node.js API to production for a client project. I'd built it entirely with AI assistance, never having touched JavaScript beyond basic jQuery years ago. Everything worked great until I started getting weird memory leaks under load.

Guess what happened when I tried to debug it? Complete disaster. I didn't understand async/await, had no clue about event loop blocking, and couldn't read stack traces. What should have been a two-hour fix turned into a week-long scramble to find a Node.js consultant.

That's the dark side of this whole thing. When I don't understand the underlying language, debugging becomes nearly impossible. Error messages might as well be written in Sanskrit. Performance problems are mysteries. Security vulnerabilities are invisible.

I've shipped code with SQL injection vulnerabilities because I didn't understand parameterized queries. I accidentally created infinite loops in Python because I didn't grasp how iterators work.

The AI gives me superpowers, but it doesn't give me judgment.

## Finding the Middle Ground

So what's the right approach here? I think it comes down to being smart about my ignorance.

Before I touch a new language with AI assistance, I spend maybe half a day getting oriented. Not becoming an expert, just understanding the basics. What's the syntax look like? How does error handling work? What are the common gotchas?

For Python, that means understanding indentation, basic data types, and how FastAPI decorators work. For JavaScript, it's hoisting, closures, and the event loop (even if just conceptually). For any framework with RAG patterns, it's vector embeddings, retrieval systems, and context windows.

I don't need to be fluent. I just need enough context to spot when something looks fishy.

I also make it a rule to actually read every line of AI-generated code before running it. Not just skimming, but really reading. What's this function doing? Why is it structured this way? Does this make sense given what I'm trying to accomplish?

## When to Just Say No

There are definitely times when this whole approach is a terrible idea.

If I'm building anything that handles sensitive data, I better understand the security implications of every line of code. If performance matters (like, really matters), I need to know the language's performance characteristics inside and out. If other people are going to maintain my code, it needs to follow patterns they can understand and extend.

I learned this the hard way on a client project two years ago. I built a "quick" data processing script in Scala using AI assistance. Six months later, when they needed modifications, none of their Java developers could make sense of what I'd created. It worked perfectly, but it was unmaintainable.

## What This Means Going Forward

I think we're heading toward a world where the ability to collaborate effectively with AI becomes as important as traditional programming skills. Maybe more important.

But that doesn't mean traditional skills become irrelevant. If anything, having a solid foundation in programming principles becomes more valuable because it helps me guide and evaluate AI output.

The developers who thrive in this new world won't necessarily be the ones who know the most languages. They'll be the ones who best understand how to combine human intuition with AI capability.

## The Real Talk

Here's my honest take: it's totally fine to use AI when working with languages you don't know well. Just don't pretend you're an expert in those languages afterward.

I'm upfront about my limitations. When something breaks (and it will), I'm not too proud to ask for help from someone who actually knows what they're doing. And if a project starts getting serious, I invest the time to learn properly or bring in real expertise.

The goal isn't to replace learning with AI. It's to use AI to learn faster and accomplish more while I'm building that expertise.

I still think my portfolio chatbot was impressive for the initial working version, even though I spent days tweaking and improving it afterward. The iterative process of building, testing, and refining taught me more about Python and FastAPI than any tutorial could have.

That feels like the right balance to me.