/**************************************************************************
* Otter Browser: Web browser controlled by the user, not vice-versa.
* Copyright (C) 2018 Michal Dutkiewicz aka Emdek <michal@emdek.pl>
*
* This program is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program. If not, see <http://www.gnu.org/licenses/>.
*
**************************************************************************/

#include "FeedsManager.h"
#include "SessionsManager.h"
#include "Utils.h"

namespace Otter
{

Feed::Feed(const QString &title, const QUrl &url, const QIcon &icon, int updateInterval, QObject *parent) : QObject(parent),
	m_title(title),
	m_url(url),
	m_icon(icon),
	m_error(NoError),
	m_updateInterval(updateInterval)
{
}

void Feed::update()
{
// TODO
}

QString Feed::getTitle() const
{
	return m_title;
}

QString Feed::getDescription() const
{
	return m_description;
}

QUrl Feed::getUrl() const
{
	return m_url;
}

QIcon Feed::getIcon() const
{
	return m_icon;
}

QDateTime Feed::getLastUpdateTime() const
{
	return m_lastUpdateTime;
}

QDateTime Feed::getLastSynchronizationTime() const
{
	return m_lastSynchronizationTime;
}

QStringList Feed::getCategories() const
{
	return m_categories;
}

QVector<Feed::Entry> Feed::getEntries()
{
	return m_entries;
}

Feed::FeedError Feed::getError() const
{
	return m_error;
}

int Feed::getUpdateInterval() const
{
	return m_updateInterval;
}

FeedsManager* FeedsManager::m_instance(nullptr);
FeedsModel* FeedsManager::m_model(nullptr);
QVector<Feed*> FeedsManager::m_feeds;
bool FeedsManager::m_isInitialized(false);

FeedsManager::FeedsManager(QObject *parent) : QObject(parent),
	m_saveTimer(0)
{
}

void FeedsManager::timerEvent(QTimerEvent *event)
{
	if (event->timerId() == m_saveTimer)
	{
		killTimer(m_saveTimer);

		m_saveTimer = 0;

		if (m_model)
		{
			m_model->save(SessionsManager::getWritableDataPath(QLatin1String("feeds.opml")));
		}
	}
}

void FeedsManager::createInstance()
{
	if (!m_instance)
	{
		m_instance = new FeedsManager(QCoreApplication::instance());
	}
}

void FeedsManager::ensureInitialized()
{
	if (m_isInitialized)
	{
		return;
	}

	m_isInitialized = true;

	if (!m_model)
	{
		m_model = new FeedsModel(SessionsManager::getWritableDataPath(QLatin1String("feeds.opml")), m_instance);
	}
}

void FeedsManager::scheduleSave()
{
	if (m_saveTimer == 0)
	{
		m_saveTimer = startTimer(1000);
	}
}

FeedsManager* FeedsManager::getInstance()
{
	return m_instance;
}

FeedsModel* FeedsManager::getModel()
{
	ensureInitialized();

	return m_model;
}

Feed* FeedsManager::createFeed(const QString &title, const QUrl &url, const QIcon &icon, int updateInterval)
{
	ensureInitialized();

	Feed *feed(getFeed(url));

	if (feed)
	{
		return feed;
	}

	feed = new Feed(title, url, icon, updateInterval, m_instance);

	m_feeds.append(feed);

	connect(feed, &Feed::feedModified, m_instance, &FeedsManager::scheduleSave);

	return feed;
}

Feed* FeedsManager::getFeed(const QUrl &url)
{
	ensureInitialized();

	const QUrl normalizedUrl(Utils::normalizeUrl(url));

	for (int i = 0; i < m_feeds.count(); ++i)
	{
		Feed *feed(m_feeds.at(i));

		if (m_feeds.at(i)->getUrl() == url || m_feeds.at(i)->getUrl() == normalizedUrl)
		{
			return feed;
		}
	}

	return nullptr;
}

QVector<Feed*> FeedsManager::getFeeds()
{
	ensureInitialized();

	return m_feeds;
}

}